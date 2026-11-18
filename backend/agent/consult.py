"""리포트 하단 '돌몽이 상담' — 은행 앱 상담 챗봇처럼, LLM 없이 규칙 + 데이터로만 답한다.

- 지금 보고 있는 동네(region_id)와 조건(conditions)을 알고 시작한다. 질문에 다른 동네 이름이 있으면 그 동네로.
- 질문 → 분류(INTENTS 정규식) → 도구/데이터로 답 → 출처 표시. 지어낸 숫자·장소는 없다.
- 데이터로 답할 수 없는 질문은 제주도 공식 문의처로 안내한다.
- LLM 을 쓰지 않는 이유: 토큰 비용 0, 답이 항상 우리 데이터에서만 나온다(환각 없음), 키 유출 위험 없음.

데이터 (data/processed)
  consult_counts.csv  동네별 시설 수 (793 상가 업종, 859 병·의원, 812 박물관, 352·201 놀이터, 956 민박, 25 레저업체 등)
  consult_places.csv  동네별 대표 시설 (병원·소아 진료·응급실·심야약국·레저업체·박물관·놀이터)
  attractions.csv     관광지 인기 (912 관광상품 구매·아이 동반 비율·평점, 905 구글 관광지 리뷰 수, 1349 VISIT JEJU 여행장소)
  lodging.csv         숙소 (910 숙박 예약 — 1박 평균 금액·예약 수), lodging_summary.csv 동네별 1박 중앙값
  region_places.csv   맛집·카페(구글 지도 링크)·오름·도서관·오일장 (리허설과 같은 데이터)
"""
import math
import re
from dataclasses import replace
from datetime import date
from functools import lru_cache
from urllib.parse import quote_plus

import pandas as pd

from backend import config
from backend.schema import Conditions
from backend.tools.cost import COST, estimate_total_cost
from backend.tools.jeju import jeju
from backend.tools.data_loader import find_region_ids, load_regions
from backend.tools.region import get_region_detail, label, rank_regions
from backend.tools.savings import suggest_savings

P = config.ROOT_DIR / "data" / "processed"

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
    {"id": "cons", "label": "🤔 이 동네 단점"},
    {"id": "transit", "label": "🚌 차 없이 살 만해요?"},
    {"id": "food", "label": "🍜 맛집·카페"},
    {"id": "lodging", "label": "🏠 숙소 시세"},
    {"id": "beginner", "label": "🌱 제주 초보 추천"},
    {"id": "kids", "label": "🧒 아이랑 갈 곳"},
    {"id": "medical", "label": "🏥 병원·응급실"},
    {"id": "season", "label": "📅 언제 가면 좋아요?"},
    {"id": "compare", "label": "⚖️ 추천 동네 장단점"},
    {"id": "contact", "label": "☎️ 문의처 안내"},
]

FACTOR_WORDS = {"밤길안심": r"치안|안전|밤길|cctv|CCTV", "교통": r"교통|버스", "의료": r"의료|병원",
                "자연": r"자연|오름|바다|해변", "조용함": r"조용|한적", "맛집": r"맛집|식당",
                "날씨": r"날씨|따뜻", "생활편의": r"편의|편리|마트"}

AMENITY_WORDS = [  # (정규식, 793 상가 업종 소분류)
    (r"빨래방|코인\s*세탁|셀프\s*빨래", "셀프 빨래방"), (r"세탁소|드라이", "세탁소"), (r"헬스|피트니스|운동", "헬스장"),
    (r"요가|필라테스", "요가/필라테스 학원"), (r"수영장", "수영장"), (r"약국", "약국"), (r"마트|슈퍼|장보", "슈퍼마켓"),
    (r"편의점", "편의점"), (r"목욕|사우나|찜질", "목욕탕/사우나"), (r"스터디\s*카페|독서실", "독서실/스터디 카페"),
    (r"동물\s*병원", "동물병원"), (r"빵집|베이커리|빵", "빵/도넛"), (r"볼링", "볼링장"), (r"애견|펫\s*샵|애완", "애완동물/애완용품 소매업"),
]

ACTIVITY = {  # 활동 → (찾을 곳, 이름 키워드)
    "요트": ("leisure", "요트"), "잠수함": ("leisure", "잠수"), "유람선": ("leisure", "유람선"),
    "낚시": ("attraction", "낚시"), "카약": ("attraction", "카약"), "돌고래": ("attraction", "돌고래"),
    "레일바이크": ("attraction", "레일바이크"), "카트": ("attraction", "카트"), "제트보트": ("attraction", "제트보트"),
    "캠핑": ("places", "camping"), "오름": ("places", "oreum"), "등산": ("places", "oreum"),
    "박물관": ("counts", "museum"), "미술관": ("counts", "museum"), "해수욕": ("beach", ""), "물놀이": ("beach", ""),
    "축제": ("festival", ""),
}
NO_DATA_ACTIVITY = r"서핑|승마|말\s*타|스노클|다이빙|패러|스쿠버|골프|클라이밍|SUP|패들"

INTENTS = [  # 위에서부터 먼저 맞는 것
    ("contact", r"문의|전화번호|연락처|상담원|사람이랑"),
    ("car_cost", r"(렌트|렌터카|차\s*빌|차를?\s*(추가|쓰|빌))[^?]*(얼마|비용|증가|더\s*들|늘)"),
    ("priority_cost", r"(" + "|".join(FACTOR_WORDS.values()) + r")[^?]*(챙기|중요|우선|신경|좋은\s*곳)[^?]*(비용|얼마|돈|더\s*들)"),
    ("one_on_one", r"1\s*대\s*1|일대일|비슷한\s*(예산|가격|비용)|맞비교"),
    ("compare_pc", r"장단점"),
    ("save", r"예산|줄이|줄일|아끼|아낄|저렴|싸게|절약|비용.*(낮|줄)"),
    ("season", r"시기|언제|몇\s*월|계절|어느\s*달|무슨\s*달"),
    ("lodging", r"숙소|숙박|호텔|펜션|민박|잘\s*곳|묵을"),
    ("gyul", r"귤|감귤|한라봉|만감|천혜향"),
    ("medical", r"병원|소아과|응급|아프|다치|의원|진료|심야\s*약국"),
    ("amenity", "|".join(p for p, _ in AMENITY_WORDS)),
    ("activity_nodata", NO_DATA_ACTIVITY),
    ("activity", "|".join(ACTIVITY)),
    ("food", r"맛집|식당|먹을|밥집|카페|커피|맛있는"),
    ("kids", r"아이|아기|애기|애들|어린이|키즈|자녀|가족"),
    ("beginner", r"초보|처음|첫\s*방문|가볼\s*만|가볼만|추천하는\s*곳|추천\s*장소"),
    ("hotplace", r"핫플|인기|유명|요즘|뜨는|관광지|명소|볼거리"),
    ("cons", r"단점|안\s*좋|아쉬운|불편한\s*점|나쁜\s*점|별로"),
    ("compare", r"장단점|비교|다른\s*동네|대신|어디가\s*나|더\s*나은"),
    ("transit", r"버스|차\s*없|뚜벅|대중교통|걸어|도보|교통"),
    ("safety", r"치안|밤길|cctv|CCTV|안전|위험"),
    ("why", r"왜|근거|어떻게\s*계산|산정|이유|점수|어떻게\s*나온"),
    ("out", r"계약|보증금|전입|주민등록|세금|지원금|보조금|분쟁|보험|비자|취업|전학|쓰레기|분리수거|배차|시간표"),
]


# ── 공통 ────────────────────────────────────────────────
@lru_cache
def _csv(name):
    p = P / f"{name}.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def _won(v) -> str:
    return f"{int(round(v)):,}만 원"


def _krw(v) -> str:
    return f"{int(round(v / 1000)) * 1000:,}원"


def _eun(word: str) -> str:
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


def _gmap(q: str) -> str:
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(q)


def _link(name: str, url: str | None = None) -> str:
    return f"[{name}]({url or _gmap('제주 ' + name)})"


def _find(region_id: str, cond: Conditions):
    ranked = rank_regions(cond, top_k=14)
    return next((r for r in ranked["results"] if r["region_id"] == region_id), None), ranked


def _row(rid) -> dict:
    return get_region_detail(rid)


def _km(a: dict, b: dict) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _count(rid, kind) -> int:
    c = _csv("consult_counts")
    m = c[(c.region_id == rid) & (c.kind == kind)]
    return int(m.n.iloc[0]) if len(m) else 0


def _rank_of(kind, rid) -> int:
    c = _csv("consult_counts")
    vals = {r: _count(r, kind) for r in load_regions().index}
    return sorted(vals, key=lambda r: -vals[r]).index(rid) + 1


def _places(rid, kind):
    d = _csv("consult_places")
    return d[(d.region_id == rid) & (d.kind == kind)].to_dict("records")


def _rp(rid, kind):
    d = _csv("region_places")
    return d[(d.region_id == rid) & (d.kind == kind)].to_dict("records")


def _ranked_result(region_id, cond):
    """rank_regions 결과 중 이 동네 (예산 초과로 빠졌으면 예산을 풀고 다시)."""
    r, ranked = _find(region_id, cond)
    if r is None:
        r, ranked = _find(region_id, replace(cond, budget_total=None))
    return r, ranked


# ── 비용 ────────────────────────────────────────────────
def _answer_save(region_id, cond, text):
    target = _target(text)
    s = suggest_savings(region_id, cond, target)
    lines = [f"지금 조건이면 **{s['region_name']}** 예상 비용은 **{_won(s['total'])}**이에요."]
    big = max(s["breakdown"], key=s["breakdown"].get)
    lines.append(f"가장 큰 항목은 {big}({_won(s['breakdown'][big])})예요.")
    lines.append(f"**{target}만 원**을 줄이려면 이렇게 할 수 있어요:" if target else "계산식으로 다시 돌려 보니 이렇게 줄일 수 있어요:")
    for i, o in enumerate(s["options"][:4], 1):
        ok = " ✅" if target and o["saved"] >= target else ""
        lines.append(f"{i}. **{o['label']}** → {_won(o['saved'])} 절약 (총 {_won(o['new_total'])}){ok}")
        lines.append(f"   └ {o['how']}" + (f" · {o['caveat']}" if o["caveat"] else ""))
    if s["combo"]:
        lines.append(f"한 가지로는 부족해서 **{s['combo']['label']}**을 같이 하면 {_won(s['combo']['saved'])} 줄어요 (총 {_won(s['combo']['new_total'])}).")
    if target and not any(o["saved"] >= target for o in s["options"]) and not (s["combo"] and s["combo"]["saved"] >= target):
        lines.append(f"계산식 안에서는 {target}만 원을 한 번에 줄이기 어려워요. 기간을 줄이거나 인원을 나누는 것도 방법이에요.")
    lines.append(s["fixed_note"])
    return lines, ["비용 계산식 docs/COST_MODEL.md", "국토부 전월세 실거래가(임대지수)", "jeju.com 2026 한달살이 가이드"], ["lodging", "season", "transit"]


def _answer_car_cost(region_id, cond, text):
    row = _row(region_id)
    with_car = estimate_total_cost(region_id, replace(cond, car=True))
    no_car = estimate_total_cost(region_id, replace(cond, car=False))
    diff = with_car["total"] - no_car["total"]
    allr = [estimate_total_cost(r, replace(cond, car=True))["total"] - estimate_total_cost(r, replace(cond, car=False))["total"]
            for r in load_regions().index]
    months = sorted({(cond.resolved_start().month + i - 1) % 12 + 1 for i in range(0, max(1, math.ceil(cond.days / 30)))})
    lines = [f"**{row['name']}**에서 {cond.days}일 지내면 렌터카를 더하면 **{_won(diff)}** 늘어요 "
             f"(버스 {_won(no_car['total'])} → 렌터카 {_won(with_car['total'])}).",
             f"제주 14개 동네 평균으로도 {_won(sum(allr) / len(allr))} 늘어요. 렌터카 단가는 동네가 아니라 달에 따라 달라서 거의 같아요.",
             "└ 렌터카 월 단가: 1·2월 50만, 3월 40만, 7·8월 100만 원 등 (머무는 달: " + ", ".join(f"{m}월" for m in months) + ")",
             f"└ 버스는 1인 월 {COST['bus_month_per_person']}만 원 × {cond.people}명으로 계산해요."]
    if row["bus_stops"] < 250:
        lines.append(f"이 동네는 정류장이 {int(row['bus_stops'])}곳뿐이라 차가 있으면 훨씬 편해요.")
    return lines, ["비용 계산식 docs/COST_MODEL.md", "jeju.com 2026 가이드(렌터카 단가)", "제주데이터허브 612 버스 정류소"], ["save", "transit"]


def _answer_priority_cost(region_id, cond, text):
    factor = next((f for f, p in FACTOR_WORDS.items() if re.search(p, text)), "밤길안심")
    pri = [factor] + [p for p in cond.priorities if p != factor][:2]
    now, _ = _ranked_result(region_id, cond)
    _, ranked = _find(region_id, replace(cond, priorities=pri, budget_total=None))
    top = ranked["results"][0]
    best_f = max(ranked["results"], key=lambda r: r["living_scores"].get(factor, 0))
    lines = [f"**{label(factor)}**을(를) 가장 중요하게 놓고 다시 계산해 봤어요."]
    lines.append(f"- 지금 동네 **{now['name']}**: {label(factor)} {now['living_scores'][factor]:.2f}점, {_won(now['cost']['total'])}")
    for o in [top] + ([best_f] if best_f["region_id"] != top["region_id"] else []):
        d = o["cost"]["total"] - now["cost"]["total"]
        tag = "새 1위" if o is top else f"{label(factor)} 1위"
        lines.append(f"- {tag} **{o['name']}**: {label(factor)} {o['living_scores'][factor]:.2f}점, {_won(o['cost']['total'])} "
                     f"({'+' if d >= 0 else ''}{d:,}만 원)")
        if o["evidence"]["living"].get(factor, {}).get("reason"):
            lines.append(f"   └ {o['evidence']['living'][factor]['reason']}")
    lines.append("비용 차이는 숙소비(임대지수) 차이가 대부분이에요.")
    return lines, [now["evidence"]["living"][factor]["data"]], ["why", "save", "compare"]


# ── 동네 비교 ────────────────────────────────────────────
def _pros_cons(r):
    ls = r["living_scores"]
    ev = r["evidence"]["living"]
    best = sorted(ls, key=ls.get, reverse=True)[:2]
    worst = sorted(ls, key=ls.get)[:2]
    pro = " / ".join(f"{label(k)}({ev[k]['reason']})" if ev[k].get("reason") else label(k) for k in best if ls[k] >= 0.6)
    con = " / ".join(f"{label(k)}({ev[k]['reason']})" if ev[k].get("reason") else label(k) for k in worst if ls[k] <= 0.4)
    return pro or "눈에 띄는 강점 없음", con or "눈에 띄는 약점 없음"


def _answer_compare(region_id, cond, text):
    _, ranked = _ranked_result(region_id, cond)
    lines = ["추천 동네 상위 3곳의 장단점이에요 (생활 점수 최고·최저 항목):"]
    for o in ranked["results"][:3]:
        pro, con = _pros_cons(o)
        lines.append(f"**{o['name']}** {o['score']}점 · {_won(o['cost']['total'])}")
        lines.append(f"   └ 👍 {pro}")
        lines.append(f"   └ 👎 {con}")
    if region_id not in [o["region_id"] for o in ranked["results"][:3]]:
        r, _ = _ranked_result(region_id, cond)
        pro, con = _pros_cons(r)
        lines.append(f"(지금 보는 **{r['name']}**: 👍 {pro} · 👎 {con})")
    return lines, ["제주데이터허브 지표 → docs/DATA.md '추천 점수'"], ["one_on_one", "cons", "why"]


def _answer_one_on_one(region_id, cond, text):
    r, ranked = _ranked_result(region_id, cond)
    others = [o for o in ranked["results"] if o["region_id"] != region_id]
    named = [i for i in find_region_ids(text) if i != region_id]
    o = next((x for x in others if x["region_id"] in named), None) or min(others, key=lambda x: abs(x["cost"]["total"] - r["cost"]["total"]))
    lines = [f"**{r['name']}** vs **{o['name']}**" + ("" if named else " (예산이 가장 비슷한 동네)"),
             f"- 총비용: {_won(r['cost']['total'])} vs {_won(o['cost']['total'])}",
             f"- 추천 점수: {r['score']}점 vs {o['score']}점"]
    for k in r["living_scores"]:
        a, b = r["living_scores"][k], o["living_scores"][k]
        mark = "◀" if a - b >= 0.15 else "▶" if b - a >= 0.15 else "＝"
        lines.append(f"- {label(k)}: {a:.2f} {mark} {b:.2f}")
    wins_a = sum(1 for k in r["living_scores"] if r["living_scores"][k] - o["living_scores"][k] >= 0.15)
    wins_b = sum(1 for k in r["living_scores"] if o["living_scores"][k] - r["living_scores"][k] >= 0.15)
    lines.append(f"뚜렷하게 앞서는 항목: {r['name']} {wins_a}개, {o['name']} {wins_b}개 (0.15점 이상 차이)")
    return lines, ["추천 점수 docs/DATA.md"], ["compare", "save"]


def _answer_cons(region_id, cond, text):
    r, _ = _ranked_result(region_id, cond)
    ls, ev = r["living_scores"], r["evidence"]["living"]
    weak = [k for k in sorted(ls, key=ls.get) if ls[k] <= 0.45][:3]
    lines = [f"**{r['name']}**에서 아쉬울 수 있는 점이에요:"]
    for k in weak:
        lines.append(f"- **{label(k)}** {ls[k]:.2f}점: {ev[k].get('reason') or ''}")
    for w in r["warnings"]:
        lines.append(f"- ⚠️ {w}")
    for key, v in r["indices"].items():
        if v.get("tone") == "warn":
            lines.append(f"- ⚠️ {v['text']}")
    if len(lines) == 1:
        lines.append("지표상 크게 떨어지는 항목은 없어요.")
    return lines, ["생활 점수·세심 체크·동네 지수 (docs/DATA.md)"], ["compare", "why"]


def _answer_why(region_id, cond, text):
    r, ranked = _ranked_result(region_id, cond)
    w = r["evidence"]["weights"]
    tot = sum(w.values()) or 1
    top_w = sorted(w.items(), key=lambda x: -x[1])[:3]
    lines = [f"**{_eun(r['name'])}** 100점 만점에 **{r['score']}점**이에요. 항목별 점수(0~1)를 가중치로 평균했어요."]
    lines.append("가중치가 큰 항목: " + ", ".join(f"{label(k)} {v / tot:.0%}" for k, v in top_w)
                 + (" (직접 고른 우선순위)" if cond.priorities else " (조건으로 추정)"))
    lines.append(f"- 비용 점수 {r['cost_score']:.2f}: 추천 동네 중 가장 싼 곳 대비 % 차이로 매겨요 (50% 비싸면 0점)")
    for k, ev in r["evidence"]["living"].items():
        if w.get(k, 0) / tot >= 0.05:
            lines.append(f"- **{label(k)}** {r['living_scores'][k]:.2f}: {ev['how']}")
            lines.append(f"   └ 출처: {ev['data']}")
    return lines, ["docs/DATA.md '추천 점수'"], ["cons", "compare", "save"]


# ── 생활 ────────────────────────────────────────────────
def _answer_transit(region_id, cond, text):
    row = _row(region_id)
    r, _ = _ranked_result(region_id, cond)
    ev = r["evidence"]["living"]["교통"]
    lines = [f"**{row['name']}** 교통 점수는 {r['living_scores']['교통']:.2f}점이에요. {ev['how']}."]
    if row["bus_stops"] >= 400:
        lines.append("정류장이 많은 편이라 차 없이도 지낼 만해요.")
    elif row["bus_stops"] < 250:
        lines.append("정류장이 적은 편이라 차 없이 지내면 배차를 꼭 확인해야 해요.")
    lines.append(f"걸어서 장보기: 슈퍼마켓 {_count(region_id, 'amenity:슈퍼마켓')}곳, 편의점 {_count(region_id, 'amenity:편의점')}곳 (793 상가정보)")
    s = suggest_savings(region_id, cond)
    car = next((o for o in s["options"] if o["key"] == "car"), None)
    if car:
        lines.append(f"렌터카 대신 버스로 지내면 **{_won(car['saved'])}** 아낄 수 있어요.")
    lines.append(f"출처: {ev['data']}")
    lines.append("버스 시간표·배차는 제가 가진 데이터에 없어요 → " + _contact_lines(["general"])[0])
    return lines, [ev["data"]], ["car_cost", "save", "amenity"]


def _answer_amenity(region_id, cond, text):
    row = _row(region_id)
    cats = [c for p, c in AMENITY_WORDS if re.search(p, text)] or ["슈퍼마켓", "편의점", "셀프 빨래방", "헬스장", "약국"]
    lines = [f"**{row['name']}** 주변 생활 시설이에요 (793 상가정보, 2025-09):"]
    for c in cats[:5]:
        n = _count(region_id, f"amenity:{c}")
        lines.append(f"- **{c}** {n}곳 — 14개 동네 중 {_rank_of(f'amenity:{c}', region_id)}위 · {_link('지도에서 보기', _gmap(f'제주 {row['name']} {c}'))}")
    if "셀프 빨래방" in cats and _count(region_id, "amenity:셀프 빨래방") <= 3:
        lines.append("빨래방이 적은 편이라 세탁기 있는 숙소를 고르는 게 좋아요.")
    return lines, ["제주데이터허브 793 상가(상권) 정보"], ["transit", "medical"]


def _answer_medical(region_id, cond, text):
    row = _row(region_id)
    health = "health_sgp" if row["city"] == "서귀포시" else "health_jeju"
    lines = [f"**{row['name']}**: 영업 중 병·의원 {int(row['hospital_cnt'])}곳, 소아 진료 {int(row['pediatric_cnt'])}곳, "
             f"응급실까지 차로 약 {int(row['er_drive_min'])}분(추정)이에요."]
    hs = _places(region_id, "hospital")
    if hs:
        lines.append("가까운 병원·보건소:")
        lines += [f"- {_link(h['name'])} ({h['sub']}) {h['addr']}" for h in hs[:4]]
    ks = _places(region_id, "kids_clinic")
    if ks and (cond.with_kids or re.search(r"아이|소아|애", text)):
        lines.append("소아청소년과 진료과목이 있는 의원:")
        lines += [f"- {_link(k['name'])} {k['addr']}" for k in ks[:3]]
    ers = _places(region_id, "er")
    if not ers:  # 동네에 응급실이 없으면 가장 가까운 응급실
        allers = _csv("consult_places")
        allers = allers[allers.kind == "er"]
        df = load_regions()
        here = df.loc[region_id]
        ers = sorted(allers.to_dict("records"), key=lambda e: _km(here, df.loc[e["region_id"]]))[:2]
        lines.append("가장 가까운 응급실 (동네 중심 거리 기준):")
    else:
        lines.append("응급실:")
    lines += [f"- 🚑 {_link(e['name'])} {e['addr']} ☎ {e['extra']}" for e in ers[:3]]
    ph = _places(region_id, "night_pharmacy")
    if ph:
        lines.append(f"심야약국: {ph[0]['name']} ({ph[0]['extra']}까지, {ph[0]['sub']})")
    lines += ["진료 시간·예방접종은 보건소가 정확해요:", *_contact_lines([health, "emergency"])]
    return lines, ["제주데이터허브 859 병·의원(2025-09), 1046 응급실, 216 공공심야약국"], ["kids", "contact"]


def _answer_lodging(region_id, cond, text):
    row = _row(region_id)
    c = estimate_total_cost(region_id, cond)
    lines = [f"**{row['name']}** 숙소 이야기예요."]
    lines.append(f"- 우리 계산식의 숙소비: **{_won(c['breakdown']['숙소'])}** ({c['tier']} 기준, 임대지수 {row['rent_index']})")
    s = _csv("lodging_summary")
    m = s[s.region_id == region_id]
    if len(m):
        lines.append(f"- 단기 예약 1박 중앙값: **{_krw(m.median_per_night.iloc[0])}** (예약된 숙소 {int(m.lodgings.iloc[0])}곳, 910 숙박 예약 데이터)")
    lo = _csv("lodging")
    tops = lo[lo.region_id == region_id].sort_values("bookings", ascending=False).head(4)
    if len(tops):
        lines.append("예약이 많았던 숙소:")
        lines += [f"- {_link(t['name'])} ({t['type']}) 1박 평균 {_krw(t['per_night'])} · 예약 {int(t['bookings'])}건" for _, t in tops.iterrows()]
    mb = _count(region_id, "minbak")
    if mb:
        lines.append(f"- 농어촌 민박 {mb}곳 등록 (956, 제주시 지역만) — 한 달 단위로 협상하기 좋아요.")
    lines.append("※ 910은 관광 숙박 예약 기록이라 한 달살이 장기 계약가와는 달라요. 장기 계약은 우리 비용 계산식(임대지수)을 참고하세요.")
    return lines, ["제주데이터허브 910 숙박 예약(2020~2021), 956 농어촌 민박, 국토부 전월세 실거래가"], ["save", "season"]


def _answer_food(region_id, cond, text):
    row = _row(region_id)
    foods, cafes = _rp(region_id, "food"), _rp(region_id, "cafe")
    lines = [f"**{row['name']}** 평점 높은 곳이에요 (구글 리뷰 20건 이상, 평점순):"]
    if foods:
        lines.append("🍜 식당")
        lines += [f"- {_link(f['name'], f.get('url'))} ★{f['rating']:.1f} (리뷰 {int(f['reviews'])})" for f in foods[:4]]
    if cafes:
        lines.append("☕ 카페")
        lines += [f"- {_link(f['name'], f.get('url'))} ★{f['rating']:.1f} (리뷰 {int(f['reviews'])})" for f in cafes[:3]]
    lines.append(f"20년 넘은 노포 비율 {float(row.get('nopo_ratio') or 0):.0%} (780 음식점 인허가)")
    lines.append("※ 구글 리뷰는 2021년 기준이라 지금은 문을 닫았을 수 있어요.")
    return lines, ["제주데이터허브 906 구글 음식점 리뷰, 780 음식점 목록"], ["hotplace", "beginner"]


def _answer_gyul(region_id, cond, text):
    df = load_regions()
    g = df.dropna(subset=["gyul_brix"])
    g = g[g.gyul_samples >= 3].sort_values("gyul_brix", ascending=False)
    lines = ["감귤 당도 검사 결과(857, 2020년 11~12월 고품질 감귤)로 보면:"]
    for rid, r in g.head(4).iterrows():
        lines.append(f"- **{r['name']}** 평균 {r['gyul_brix']:.1f}Brix (검사 {int(r['gyul_samples'])}건)")
    here = df.loc[region_id]
    if pd.notna(here.get("gyul_brix")):
        lines.append(f"지금 동네 {here['name']}: {here['gyul_brix']:.1f}Brix (검사 {int(here['gyul_samples'])}건)")
    gm = _csv("gyul_month")
    m = cond.resolved_start().month
    now = gm[(gm.month == m) & (gm.share >= 0.1)].sort_values("share", ascending=False)
    if len(now):
        lines.append(f"{m}월에 많이 나오는 품종: " + ", ".join(f"{v} ({s:.0%})" for v, s in zip(now.variety, now.share)) + " (855 출하량)")
    lines.append("농장별 맛은 데이터가 없어요. 오일장·농협 하나로마트 직판장에서 그 철 품종을 사는 게 좋아요.")
    mk = _rp(region_id, "market")
    if mk:
        lines.append("근처 시장: " + ", ".join(f"{x['name']}" + (f"(끝자리 {x['extra']}일)" if str(x.get('extra')) not in ("매일", "nan") else "(매일)") for x in mk))
    return lines, ["제주데이터허브 857 감귤 당도, 855 감귤 출하량, 985 전통시장"], ["season", "food"]


# ── 놀거리 ──────────────────────────────────────────────
def _attractions(rid):
    a = _csv("attractions")
    a = a[a.region_id == rid].copy()
    a["pop"] = a.reviews.fillna(0) + a.tickets.fillna(0)
    return a.sort_values("pop", ascending=False)


def _attr_line(t):
    bits = []
    if pd.notna(t["reviews"]):
        bits.append(f"구글 리뷰 {int(t['reviews'])}")
    if pd.notna(t["tickets"]):
        bits.append(f"티켓 구매 {int(t['tickets'])}건")
    if pd.notna(t["score"]):
        bits.append(f"평점 {t['score']}")
    return f"- {_link(t['name'])}" + (f" ({t['type']})" if isinstance(t["type"], str) else "") + (" · " + ", ".join(bits) if bits else "")


def _answer_hotplace(region_id, cond, text):
    row = _row(region_id)
    a = _attractions(region_id).head(6)
    lines = [f"**{row['name']}**에서 사람이 많이 찾는 곳이에요 (구글 관광지 리뷰 수 + 관광상품 구매 수):"]
    lines += [_attr_line(t) for _, t in a.iterrows()] or ["- 데이터에 잡힌 관광지가 적어요."]
    return lines, ["제주데이터허브 905 구글 관광지 리뷰(2021), 912 관광상품 구매(2020~2021), 1349 VISIT JEJU 여행장소"], ["beginner", "food", "activity"]


def _answer_beginner(region_id, cond, text):
    row = _row(region_id)
    lines = [f"제주 처음이면 **{row['name']}**에서 이렇게 시작해 보세요:"]
    a = _attractions(region_id).head(3)
    if len(a):
        lines.append("👀 많이 찾는 곳")
        lines += [_attr_line(t) for _, t in a.iterrows()]
    o = _rp(region_id, "oreum")
    if o:
        lines.append(f"⛰️ 쉬운 첫 오름: {_link(o[0]['name'])}" + (f" (관광지 리뷰 {int(o[0]['reviews'])}건)" if pd.notna(o[0].get('reviews')) and o[0]['reviews'] >= 20 else ""))
    if isinstance(row.get("beaches"), str):
        lines.append(f"🏖️ 해변: {row['beaches']}")
    f = _rp(region_id, "food")
    if f:
        lines.append(f"🍜 동네 평점 1위 식당: {_link(f[0]['name'], f[0].get('url'))} ★{f[0]['rating']:.1f}")
    mk = _rp(region_id, "market")
    if mk:
        lines.append(f"🛒 시장 구경: {mk[0]['name']}")
    lines.append("하루 일과로 보고 싶으면 위의 '한 달 살기 리허설'을 보세요.")
    return lines, ["905 관광지 리뷰, 912 관광상품, 811 오름, 784 해수욕장, 906 음식점 리뷰, 985 전통시장"], ["hotplace", "kids", "food"]


def _answer_kids(region_id, cond, text):
    row = _row(region_id)
    a = _attractions(region_id)
    kid = a[a.child_share >= 0.15].head(4)
    lines = [f"**{row['name']}**에서 아이랑 가기 좋은 곳이에요."]
    if len(kid):
        lines.append("🎟️ 아이 동반 구매가 많은 곳 (912 관광상품, 어린이·유아 티켓 비율)")
        lines += [f"- {_link(t['name'])} 아이 비율 {t['child_share']:.0%} · 구매 {int(t['tickets'])}건" for _, t in kid.iterrows()]
    else:  # 이 동네에 없으면 가까운 동네에서
        al = _csv("attractions")
        al = al[al.child_share >= 0.25].copy()
        df = load_regions()
        al["km"] = al.region_id.map(lambda r: _km(df.loc[region_id], df.loc[r]))
        near = al.sort_values(["km", "tickets"], ascending=[True, False]).head(3)
        lines.append("동네 안에는 아이 동반이 많은 관광상품이 없어서, 가까운 곳을 찾았어요:")
        lines += [f"- {_link(t['name'])} ({df.loc[t['region_id'], 'name']}, 약 {t['km']:.0f}km) 아이 비율 {t['child_share']:.0%}" for _, t in near.iterrows()]
    mus = _places(region_id, "museum")
    if mus:
        lines.append(f"🏛️ 박물관·미술관 {_count(region_id, 'museum')}곳: " + ", ".join(m["name"] for m in mus[:3]))
    pg = _places(region_id, "playground")
    if pg:
        lines.append(f"🛝 어린이공원·놀이터 {_count(region_id, 'playground')}곳: " + ", ".join(p["name"] for p in pg[:3]))
    lib = _rp(region_id, "library")
    if lib:
        lines.append(f"📚 공공도서관: {lib[0]['name']}")
    lines.append(f"🏥 소아 진료 병·의원 {int(row['pediatric_cnt'])}곳, 응급실까지 약 {int(row['er_drive_min'])}분")
    lines.append("키즈카페·실내 체험시설은 데이터가 없어요.")
    return lines, ["912 관광상품 구매(아이 동반), 812 박물관·미술관, 352·201 어린이놀이시설, 888 도서관, 859 병·의원"], ["medical", "beginner"]


def _answer_activity(region_id, cond, text):
    df = load_regions()
    here = df.loc[region_id]
    key = next(k for k in ACTIVITY if k in text)
    src, kw = ACTIVITY[key]
    found = []  # (region_id, name, extra)
    if src == "leisure":
        d = _csv("consult_places")
        found = [(r.region_id, r["name"], f"{r['sub']} · ☎ {r['extra']}") for _, r in d[(d.kind == "leisure") & d["sub"].str.contains(kw)].iterrows()]
    elif src == "attraction":
        d = _csv("attractions")
        found = [(r.region_id, r["name"], f"구매 {int(r['tickets'])}건" if pd.notna(r["tickets"]) else "") for _, r in d[d["name"].str.contains(kw)].iterrows()]
    elif src == "places":
        d = _csv("region_places")
        found = [(r.region_id, r["name"], "") for _, r in d[d.kind == kw].iterrows()]
    elif src == "counts":
        d = _csv("consult_places")
        found = [(r.region_id, r["name"], r["sub"]) for _, r in d[d.kind == kw].iterrows()]
    elif src == "beach":
        found = [(rid, b.strip() + " 해변", "") for rid, r in df.iterrows() if isinstance(r.get("beaches"), str) for b in r["beaches"].split(",")]
    elif src == "festival":
        f = _csv("festival")
        found = [(r.region_id, r["name"], f"{r['start_md']}~{r['end_md']}") for _, r in f.iterrows()]
    if not found:
        return _answer_activity_nodata(region_id, cond, text)
    found = sorted(found, key=lambda x: _km(here, df.loc[x[0]]))
    lines = [f"**{key}** 할 수 있는 곳을 {here['name']}에서 가까운 순으로 찾았어요:"]
    for rid, name, extra in found[:5]:
        km = _km(here, df.loc[rid])
        where = "이 동네" if rid == region_id else f"{df.loc[rid, 'name']} · 약 {km:.0f}km"
        lines.append(f"- {_link(name)} ({where})" + (f" {extra}" if extra else ""))
    lines.append("※ 거리는 동네 중심끼리의 직선거리예요.")
    srcs = {"leisure": "제주데이터허브 25 레저사업체현황(2021)", "attraction": "912 관광상품 구매", "places": "811 오름·810 캠핑",
            "counts": "812 박물관·미술관", "beach": "784 해수욕장", "festival": "761 VISIT JEJU 축제"}
    return lines, [srcs[src]], ["hotplace", "beginner"]


def _answer_activity_nodata(region_id, cond, text):
    m = re.search(NO_DATA_ACTIVITY, text)
    act = m.group(0) if m else "그 활동"
    lines = [f"**{act}** 업체 목록은 제가 가진 공공데이터에 없어요."]
    if re.search(r"승마|말\s*타", act):
        lines.append("참고로 신고된 승마장은 제주시 11곳, 서귀포시 7곳이에요 (162 신고체육시설업, 2024-12). 동네 단위 위치는 데이터에 없어요.")
    lines.append(f"{_link('구글 지도에서 찾아보기', _gmap('제주 ' + act))}")
    lines += ["관광 체험 업체는 관광 안내로 물어보세요:", *_contact_lines(["general"])]
    return lines, ["제주데이터허브 162 신고체육시설업"], ["hotplace", "beginner"]


# ── 시기 ────────────────────────────────────────────────
def _answer_season(region_id, cond, text):
    row = _row(region_id)
    year = date.today().year + (1 if date.today().month >= 11 else 0)
    rows = []
    for m in range(1, 13):
        c = estimate_total_cost(region_id, replace(cond, start_date=date(year, m, 1).isoformat()))
        rows.append((m, c["total"]))
    cheap = sorted(rows, key=lambda x: x[1])[:3]
    dear = max(rows, key=lambda x: x[1])
    w = _csv("weather_month")
    wm = w[w.station == row["weather_station"]].set_index("month")
    solo = cond.people == 1 or re.search(r"혼자|혼살|1인", text)
    lines = [f"**{row['name']}**에 {cond.days}일 머문다면 달마다 이렇게 달라요" + (" (혼자 기준)" if solo else "") + ":"]
    lines.append("💰 가장 싼 출발 달: " + ", ".join(f"{m}월 {_won(t)}" for m, t in cheap) + f" · 가장 비싼 달 {dear[0]}월 {_won(dear[1])}")
    if len(wm):
        good = wm.sort_values("laundry_share", ascending=False).head(3)
        lines.append("☀️ 빨래 잘 마르는(습도 낮은) 달: " + ", ".join(f"{m}월 {s:.0%}" for m, s in good.laundry_share.items()) + f" ({row['weather_station']} 관측소)")
        windy = wm.sort_values("windy_share", ascending=False).head(2)
        lines.append("🌬️ 바람 센 달: " + ", ".join(f"{m}월" for m in windy.index))
    f = _csv("festival")
    f = f[f.region_id == region_id]
    if len(f):
        fm = sorted({int(s[:2]) for s in f.start_md})
        lines.append("🎉 동네 축제가 있는 달: " + ", ".join(f"{m}월" for m in fm))
    best = [m for m, _ in cheap if m not in (7, 8)]
    if best:
        lines.append(f"정리: 비용만 보면 **{best[0]}월** 출발이 좋아요. 7·8월은 숙소 1.3배, 렌터카 100만 원이라 피하는 게 좋아요.")
    return lines, ["비용 계산식(성수기 배율)", "제주데이터허브 877 일간 기후", "761 축제"], ["save", "gyul"]


def _answer_safety(region_id, cond, text):
    r, _ = _ranked_result(region_id, cond)
    ev = r["evidence"]["living"]["밤길안심"]
    lines = [f"**{r['name']}** 안전 점수는 {r['living_scores']['밤길안심']:.2f}점이에요. {ev['how']}.",
             f"출처: {ev['data']}", "※ 112 신고 수는 범죄 건수가 아니라 교통·분실 신고까지 포함해요.",
             *_contact_lines(["emergency"])]
    return lines, [ev["data"]], ["priority_cost", "why", "contact"]


def _answer_contact(region_id, cond, text, out_of_scope=False):
    lines = (["이 질문은 제가 가진 데이터(비용 계산식·동네 지표·공공데이터)로는 정확히 답하기 어려워요. 공식 문의처로 안내할게요:"]
             if out_of_scope else ["제주도 공식 문의처예요:"])
    lines += _contact_lines(["general", "health_jeju", "health_sgp", "emergency"])
    return lines, ["제주120만덕콜센터(뉴스서울 2025-01)", "제주시·서귀포시 보건소"], ["save", "why", "beginner"]


HANDLERS = {"compare_pc": None, "save": _answer_save, "car_cost": _answer_car_cost, "priority_cost": _answer_priority_cost,
            "why": _answer_why, "cons": _answer_cons, "compare": _answer_compare, "one_on_one": _answer_one_on_one,
            "transit": _answer_transit, "amenity": _answer_amenity, "medical": _answer_medical,
            "lodging": _answer_lodging, "food": _answer_food, "gyul": _answer_gyul,
            "hotplace": _answer_hotplace, "beginner": _answer_beginner, "kids": _answer_kids,
            "activity": _answer_activity, "activity_nodata": _answer_activity_nodata,
            "season": _answer_season, "safety": _answer_safety, "contact": _answer_contact}

QR_EXTRA = {"car_cost": "🚗 렌터카 더하면 얼마?", "priority_cost": "🛡️ 안전 챙기면 얼마 더?", "one_on_one": "🥊 비슷한 예산 1대1",
            "amenity": "🧺 빨래방·헬스장", "hotplace": "🔥 핫플", "gyul": "🍊 귤", "activity": "🛥️ 해볼 만한 활동"}


def _qr(ids):
    labels = {q["id"]: q["label"] for q in QUICK} | QR_EXTRA
    return [{"id": i, "label": labels[i]} for i in ids if i in labels]


def run_consult(message: str, region_id: str, conditions: dict, intent: str | None = None, history: list | None = None) -> dict:
    cond = Conditions.from_dict(conditions or {})
    text = (message or "").strip()
    named = find_region_ids(text)
    if named:  # "추천해준 성산읍의 숙소" → 성산읍
        region_id = named[0]
    it = intent or _intent(text)
    if it == "compare_pc":
        it = "compare"
    if intent == "activity" and not any(k in text for k in ACTIVITY):  # 버튼: 대표 활동 하나
        text = "요트"
    if it in ("out", "unknown"):
        lines, sources, nxt = _answer_contact(region_id, cond, text, out_of_scope=True)
    else:
        lines, sources, nxt = HANDLERS[it](region_id, cond, text)
    return {"answer": jeju("\n".join(lines)), "intent": it, "region_id": region_id, "sources": sources,
            "quick_replies": _qr(nxt), "mode": "rule"}


def greeting(region_id: str, conditions: dict) -> dict:
    row = get_region_detail(region_id)
    return {"answer": jeju(f"안녕하세요! **{row['name']}** 리포트를 같이 볼게요. 궁금한 걸 고르거나 편하게 물어보세요.\n"
                      "예) \"예산을 30만원 정도 줄이고 싶은데, 어느 부분에서 줄여야 할까?\" · \"렌터카 추가하면 얼마 늘어?\" · \"근처에 빨래방 있어?\""),
            "intent": "hello", "sources": [], "quick_replies": [q for q in QUICK if q["id"] in ("save", "why", "cons", "transit", "food", "lodging", "kids", "season")], "mode": "rule"}
