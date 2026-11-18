"""리포트 하단 '돌몽이 상담' — 은행 앱 상담 챗봇처럼.

- 지금 보고 있는 동네(region_id)와 조건(conditions)을 알고 시작한다.
- 빠른 버튼(quick replies) → 자유 질문 → 도구 결과로만 답한다 (비용 계산식·지표·근거 데이터).
- 데이터로 답할 수 없는 질문은 제주도 공식 문의처로 안내한다.
- ANTHROPIC_API_KEY 가 있으면 Claude 가 같은 도구로 답하고, 없으면 아래 규칙 기반으로 답한다.
"""
import json
import re

from backend import config
from backend.schema import Conditions
from backend.tools.evidence import living_evidence
from backend.tools.region import FACTORS, get_region_detail, rank_regions
from backend.tools.savings import suggest_savings

# 공식 문의처 (2026-11 확인. 120만덕콜센터 매일 07~22시 — 뉴스서울 2025-01 / 보건소 번호 — 제주 장애인 재난안전 가이드북)
CONTACTS = {
    "general": {"name": "제주120만덕콜센터", "tel": "국번 없이 120", "hours": "매일 07:00~22:00",
                "for": "행정·생활·교통·관광 불편 등 제주도 전반 (관광불편신고 통합)"},
    "health_jeju": {"name": "제주시 보건소", "tel": "064-728-4010", "for": "제주시 지역 보건·예방접종"},
    "health_sgp": {"name": "서귀포시 보건소", "tel": "064-760-6001", "for": "서귀포시 지역 보건·예방접종"},
    "emergency": {"name": "119 / 112", "tel": "119 (응급·화재), 112 (범죄)", "for": "긴급 상황"},
}

QUICK = [
    {"id": "save", "label": "💰 예산 줄이는 방법"},
    {"id": "why", "label": "🔍 이 동네 추천 근거"},
    {"id": "transit", "label": "🚌 차 없이 살 만해요?"},
    {"id": "compare", "label": "⚖️ 다른 동네랑 비교"},
    {"id": "medical", "label": "🏥 병원·응급실"},
    {"id": "contact", "label": "☎️ 문의처 안내"},
]

INTENTS = [
    ("save", r"예산|줄이|줄일|아끼|아낄|저렴|싸게|절약|비용.*(낮|줄)"),
    ("contact", r"문의|전화|연락처|상담원|사람이랑"),
    ("out", r"계약|보증금|전입|주민등록|세금|지원금|보조금|신고|분쟁|법|보험|비자|취업|학교 전학|쓰레기|분리수거|버스 시간|배차"),
    ("medical", r"병원|소아|응급|아프|약국|의료"),
    ("transit", r"버스|차 없|뚜벅|교통|대중교통|렌터카"),
    ("compare", r"비교|다른 동네|대신|어디가 나|더 나은"),
    ("safety", r"치안|밤길|cctv|CCTV|안전|위험"),
    ("why", r"왜|근거|어떻게 계산|산정|이유|점수|어떻게 나온"),
]


def _won(v) -> str:
    return f"{int(round(v)):,}만 원"


def _eun(word: str) -> str:
    """받침 있으면 '은', 없으면 '는'."""
    c = word[-1]
    return word + ("은" if "가" <= c <= "힣" and (ord(c) - 0xAC00) % 28 else "는")


def _intent(text: str) -> str:
    for name, pat in INTENTS:
        if re.search(pat, text):
            return name
    return "unknown"


def _target(text: str) -> int | None:
    m = re.search(r"(\d+)\s*만", text)
    return int(m.group(1)) if m else None


def _contact_lines(keys) -> list[str]:
    out = []
    for k in keys:
        c = CONTACTS[k]
        out.append(f"☎️ **{c['name']}** {c['tel']}" + (f" ({c['hours']})" if c.get("hours") else "") + f" — {c['for']}")
    return out


def _find(region_id: str, cond: Conditions) -> dict:
    ranked = rank_regions(cond, top_k=14)
    return next((r for r in ranked["results"] if r["region_id"] == region_id), None), ranked


# ── 규칙 기반 답변 ─────────────────────────────────────────
def _answer_save(region_id, cond, text):
    target = _target(text)
    s = suggest_savings(region_id, cond, target)
    lines = [f"지금 조건이면 **{s['region_name']}** 예상 비용은 **{_won(s['total'])}**이에요."]
    big = max(s["breakdown"], key=s["breakdown"].get)
    lines.append(f"가장 큰 항목은 {big}({_won(s['breakdown'][big])})예요.")
    if target:
        lines.append(f"**{target}만 원**을 줄이려면 이렇게 할 수 있어요:")
    else:
        lines.append("계산식으로 다시 돌려 보니 이렇게 줄일 수 있어요:")
    for i, o in enumerate(s["options"][:4], 1):
        ok = " ✅" if target and o["saved"] >= target else ""
        lines.append(f"{i}. **{o['label']}** → {_won(o['saved'])} 절약 (총 {_won(o['new_total'])}){ok}")
        lines.append(f"   └ {o['how']}" + (f" · {o['caveat']}" if o["caveat"] else ""))
    if s["combo"]:
        lines.append(f"한 가지로는 부족해서 **{s['combo']['label']}**을 같이 하면 {_won(s['combo']['saved'])} 줄어요 (총 {_won(s['combo']['new_total'])}).")
    if target and not any(o["saved"] >= target for o in s["options"]) and not (s["combo"] and s["combo"]["saved"] >= target):
        lines.append(f"계산식 안에서는 {target}만 원을 한 번에 줄이기 어려워요. 기간을 줄이거나 인원을 나누는 것도 방법이에요.")
    lines.append(s["fixed_note"])
    sources = ["비용 계산식 docs/COST_MODEL.md", "국토부 전월세 실거래가(임대지수)", "jeju.com 2026 한달살이 가이드(권역 기준가·렌터카 단가)"]
    return lines, sources, ["why", "compare", "transit"]


def _answer_why(region_id, cond, text):
    r, ranked = _find(region_id, cond)
    w = r["evidence"]["weights"]
    tot = sum(w.values()) or 1
    top_w = sorted(w.items(), key=lambda x: -x[1])[:3]
    lines = [f"**{_eun(r['name'])}** 100점 만점에 **{r['score']}점**이에요. 항목별 점수(0~1)를 가중치로 평균했어요."]
    lines.append("가중치가 큰 항목: " + ", ".join(f"{k} {v / tot:.0%}" for k, v in top_w)
                 + (" (직접 고른 우선순위)" if cond.priorities else " (조건으로 추정)"))
    lines.append(f"- 비용 점수 {r['cost_score']:.2f}: 추천 동네 중 가장 싼 곳 대비 % 차이로 매겨요 (50% 비싸면 0점)")
    for k, ev in r["evidence"]["living"].items():
        if w.get(k, 0) / tot >= 0.05:
            lines.append(f"- **{k}** {r['living_scores'][k]:.2f}: {ev['how']}")
            lines.append(f"   └ 출처: {ev['data']}")
    return lines, ["docs/DATA.md '추천 점수'"], ["save", "compare", "contact"]


def _answer_transit(region_id, cond, text):
    row = get_region_detail(region_id)
    r, _ = _find(region_id, cond)
    ev = r["evidence"]["living"]["교통"]
    lines = [f"**{row['name']}** 교통 점수는 {r['living_scores']['교통']:.2f}점이에요. {ev['how']}."]
    if row["bus_stops"] >= 400:
        lines.append("정류장이 많은 편이라 차 없이도 지낼 만해요.")
    elif row["bus_stops"] < 250:
        lines.append("정류장이 적은 편이라 차 없이 지내면 배차를 꼭 확인해야 해요.")
    s = suggest_savings(region_id, cond)
    car = next((o for o in s["options"] if o["key"] == "car"), None)
    if car:
        lines.append(f"렌터카 대신 버스로 지내면 **{_won(car['saved'])}** 아낄 수 있어요.")
    lines.append(f"출처: {ev['data']}")
    lines.append("버스 시간표·배차는 제가 가진 데이터에 없어요 → " + _contact_lines(["general"])[0])
    return lines, [ev["data"]], ["save", "compare", "contact"]


def _answer_compare(region_id, cond, text):
    r, ranked = _find(region_id, cond)
    lines = [f"같은 조건에서 상위 동네와 비교해 볼게요 (지금 동네 **{r['name']}** {r['score']}점, {_won(r['cost']['total'])})."]
    for o in ranked["results"][:4]:
        if o["region_id"] == region_id:
            continue
        best = max(o["living_scores"], key=o["living_scores"].get)
        diff = o["cost"]["total"] - r["cost"]["total"]
        lines.append(f"- **{o['name']}** {o['score']}점 · {_won(o['cost']['total'])} ({'+' if diff >= 0 else ''}{diff:,}만) · 강점 {best}")
    return lines, ["추천 점수 계산 docs/DATA.md"], ["why", "save", "contact"]


def _answer_medical(region_id, cond, text):
    row = get_region_detail(region_id)
    health = "health_sgp" if row["city"] == "서귀포시" else "health_jeju"
    lines = [f"**{row['name']}**: 영업 중 병·의원 {int(row['hospital_cnt'])}곳, 소아 진료 {int(row['pediatric_cnt'])}곳, 응급실까지 약 {int(row['er_drive_min'])}분(추정)이에요.",
             "출처: 제주데이터허브 859 병·의원 정보(2025-09), 1046 응급실 보유 병원(2021-08)",
             "진료 시간·예방접종 같은 건 보건소가 정확해요:", *_contact_lines([health, "emergency"])]
    return lines, ["제주데이터허브 859, 1046"], ["why", "contact"]


def _answer_safety(region_id, cond, text):
    r, _ = _find(region_id, cond)
    ev = r["evidence"]["living"]["밤길안심"]
    lines = [f"**{r['name']}** 밤길 안심 점수는 {r['living_scores']['밤길안심']:.2f}점이에요. {ev['how']}.",
             f"출처: {ev['data']}", "※ 112 신고 수는 범죄 건수가 아니라 교통·분실 신고까지 포함해요.",
             *_contact_lines(["emergency"])]
    return lines, [ev["data"]], ["why", "contact"]


def _answer_contact(region_id, cond, text, out_of_scope=False):
    lines = (["이 질문은 제가 가진 데이터(비용 계산식·동네 지표)로는 정확히 답하기 어려워요. 공식 문의처로 안내할게요:"]
             if out_of_scope else ["제주도 공식 문의처예요:"])
    lines += _contact_lines(["general", "health_jeju", "health_sgp", "emergency"])
    return lines, ["제주120만덕콜센터(뉴스서울 2025-01)", "제주시·서귀포시 보건소"], ["save", "why"]


HANDLERS = {"save": _answer_save, "why": _answer_why, "transit": _answer_transit, "compare": _answer_compare,
            "medical": _answer_medical, "safety": _answer_safety, "contact": _answer_contact}


def run_consult(message: str, region_id: str, conditions: dict, intent: str | None = None, history: list | None = None) -> dict:
    cond = Conditions.from_dict(conditions or {})
    text = (message or "").strip()
    if config.resolved_agent_mode() == "claude" and text and not intent:
        try:
            return _claude_consult(text, region_id, cond, history)
        except Exception:  # Claude 실패 시 규칙 기반으로
            pass
    it = intent or _intent(text)
    if it in ("out", "unknown"):
        lines, sources, nxt = _answer_contact(region_id, cond, text, out_of_scope=True)
    else:
        lines, sources, nxt = HANDLERS[it](region_id, cond, text)
    return {"answer": "\n".join(lines), "intent": it, "sources": sources,
            "quick_replies": [q for q in QUICK if q["id"] in nxt], "mode": "rule"}


# ── Claude 모드: 같은 도구 + 문의처를 주고 답하게 한다 ─────────────
CONSULT_PROMPT = """너는 제주살이 AI Agent '돌몽이'의 상담 창구야. 은행 앱 상담 챗봇처럼 짧고 정확하게 답해.
규칙
1. 사용자는 지금 리포트에서 동네 하나({region_id})를 보고 있어. 조건: {cond}
2. 숫자는 반드시 도구 결과에서만. 예산 질문엔 suggest_savings, 근거 질문엔 explain_region 을 먼저 불러.
3. 답 끝에 '출처:' 로 쓴 데이터(제주데이터허브 번호 등)를 적어.
4. 데이터로 답할 수 없는 질문(계약·보증금 분쟁, 전입신고, 지원금, 버스 시간표, 쓰레기 배출 세부 등)은 추측하지 말고
   get_contacts 결과의 공식 문의처를 안내해.
5. 한국어 존댓말, 5~10줄."""


def _claude_consult(text, region_id, cond, history):
    import anthropic

    tools = [
        {"name": "suggest_savings", "description": "비용 계산식을 조건만 바꿔 다시 돌려 아낄 수 있는 방법과 금액을 돌려준다.",
         "input_schema": {"type": "object", "properties": {"target": {"type": "integer", "description": "줄이고 싶은 금액(만원)"}}}},
        {"name": "explain_region", "description": "지금 동네의 점수·가중치·항목별 근거(데이터 출처와 값)를 돌려준다.",
         "input_schema": {"type": "object", "properties": {}}},
        {"name": "compare_regions", "description": "같은 조건에서 상위 동네 목록(점수·비용·강점)을 돌려준다.",
         "input_schema": {"type": "object", "properties": {}}},
        {"name": "get_contacts", "description": "제주도 공식 문의처(120만덕콜센터, 보건소, 119/112).",
         "input_schema": {"type": "object", "properties": {}}},
    ]

    def run(name, args):
        if name == "suggest_savings":
            return suggest_savings(region_id, cond, args.get("target"))
        if name == "explain_region":
            r, _ = _find(region_id, cond)
            return {k: r[k] for k in ("name", "score", "cost_score", "living_scores", "evidence", "indices")}
        if name == "compare_regions":
            _, ranked = _find(region_id, cond)
            return [{k: o[k] for k in ("name", "score", "living_scores")} | {"total": o["cost"]["total"]} for o in ranked["results"][:5]]
        return CONTACTS

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system = CONSULT_PROMPT.format(region_id=region_id, cond=json.dumps(cond.to_dict(), ensure_ascii=False))
    messages = list(history or []) + [{"role": "user", "content": text}]
    for _ in range(config.AGENT_MAX_TURNS):
        resp = client.messages.create(model=config.CLAUDE_MODEL, max_tokens=1200, system=system, tools=tools, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            answer = "".join(b.text for b in resp.content if b.type == "text")
            return {"answer": answer, "intent": "claude", "sources": [], "quick_replies": QUICK[:3], "mode": "claude"}
        results = [{"type": "tool_result", "tool_use_id": b.id,
                    "content": json.dumps(run(b.name, b.input or {}), ensure_ascii=False, default=str)}
                   for b in resp.content if b.type == "tool_use"]
        messages.append({"role": "user", "content": results})
    raise RuntimeError("too many turns")


def greeting(region_id: str, conditions: dict) -> dict:
    row = get_region_detail(region_id)
    return {"answer": f"안녕하세요! **{row['name']}** 리포트를 같이 볼게요. 궁금한 걸 고르거나 편하게 물어보세요.\n"
                      "예) \"예산을 30만원 정도 줄이고 싶은데, 어느 부분에서 줄여야 할까?\"",
            "intent": "hello", "sources": [], "quick_replies": QUICK, "mode": "rule"}
