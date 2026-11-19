"""돌몽이 상담 Agent — 리포트를 같이 읽고, 필요하면 새로 계산하고, 리포트를 고쳐 준다.

흐름 (tool-use 루프, 최대 config.AGENT_MAX_TURNS 번)
  사용자 질문 + 지금 보는 리포트 요약
    → Claude 가 도구를 고른다 (ask_data / rank_regions / compare_regions / estimate_cost / rehearse / propose_report_change ...)
    → 도구 실행 결과(우리 데이터·계산식)를 Claude 에 돌려준다
    → Claude 가 결과를 보고 다음 도구를 부르거나, 끝내고 답한다
    → 조건이 바뀌어야 맞는 상황이면 propose_report_change 로 '리포트 수정 제안'을 남긴다
      (화면에 [적용하기] 카드가 뜨고, 사용자가 누를 때만 리포트가 바뀐다)

역할 분담 (기획서 '판단 및 자율 수행 범위')
  - Claude: 질문 해석, 어떤 도구를 어떤 순서로 쓸지, 조건을 바꿔 다시 계산할지, 리포트를 바꿀지 판단 + 답 문장 구성
  - 도구(우리 코드): 모든 숫자·장소·출처. Claude 는 숫자를 만들지 않는다
  - 사용자: 최종 결정. Agent 는 리포트 수정을 '제안'만 하고, 적용은 사용자가 누를 때만. 적용 후에도 조건 폼에서 다시 바꿀 수 있다

키가 없거나 API 오류가 나면 backend.agent.consult.run_consult (규칙 + 데이터) 로 답한다.
"""
import json
import re
import time
from dataclasses import replace

from backend import config
from backend.agent import consult as rule
from backend.agent.icons import pick_icon, qr_icons, strip_emoji
from backend.schema import Conditions
from backend.tools.cost import estimate_total_cost
from backend.tools.data_loader import find_region_ids, load_regions
from backend.tools.jeju import jeju
from backend.tools.region import get_region_detail, label, list_regions, rank_regions
from backend.tools.rehearsal import rehearse

# ── 도구가 받는 '조건 바꾸기' (지금 리포트 조건에 덮어쓴다) ─────────────────
FACTORS = ["비용", "교통", "생활편의", "의료", "조용함", "자연", "날씨", "맛집", "밤길안심"]
CHANGES_SCHEMA = {
    "type": "object",
    "description": "지금 리포트 조건에서 바꿀 것만. 안 바꾸는 값은 넣지 않는다. 비우면 지금 조건 그대로.",
    "properties": {
        "start_date": {"type": "string", "description": "입도 날짜 YYYY-MM-DD (달만 말하면 그 달 1일)"},
        "days": {"type": "integer", "description": "체류 일수. 2주=14, 한 달=30, 두 달=60, 석 달=90, 반년=180, 1년=365"},
        "people": {"type": "integer", "minimum": 1, "maximum": 6},
        "car": {"type": "boolean", "description": "렌터카 true / 버스·도보 false"},
        "budget_total": {"type": ["integer", "null"], "description": "체류 전체 총예산(만 원). 예산 제한을 없애려면 null"},
        "with_kids": {"type": "boolean"}, "remote_work": {"type": "boolean"},
        "with_pet": {"type": "boolean"}, "prefer_quiet": {"type": "boolean"},
        "priorities": {"type": "array", "maxItems": 3, "items": {"type": "string", "enum": FACTORS},
                       "description": "가장 중요한 것 최대 3개, 중요한 순서대로"},
    },
}
REGION_ID = {"type": "string", "description": "region_id (리포트 요약의 동네 목록에 있음)"}

TOPICS = {  # ask_data 주제 → 규칙 상담의 데이터 조회 함수 (consult.HANDLERS)
    "save": "예산 줄이는 방법 (question 에 '30만' 처럼 목표 금액이 있으면 그만큼 줄이는 조합)",
    "car_cost": "렌터카를 더하거나 빼면 비용이 얼마나 바뀌는지",
    "priority_cost": "치안·교통·자연 등 한 가지를 가장 중요하게 놓으면 순위·비용이 어떻게 바뀌는지 (question 에 그 항목 단어 포함)",
    "why": "이 동네 추천 점수 근거, 가중치, 계산 방법",
    "cons": "이 동네 단점·주의할 점",
    "compare": "추천 상위 3곳 장단점",
    "one_on_one": "두 동네 1대1 비교 (question 에 다른 동네 이름, 없으면 예산이 비슷한 동네)",
    "transit": "차 없이 살 만한지, 버스 정류장, 걸어서 장보기",
    "amenity": "빨래방·세탁소·헬스장·요가·수영장·약국·마트·편의점·사우나·스터디카페·동물병원·빵집 개수와 순위 (question 에 시설 이름)",
    "medical": "병·의원, 소아과, 응급실, 심야약국, 보건소",
    "lodging": "숙소비, 단기 숙소 1박 시세, 예약 많은 숙소, 농어촌 민박",
    "food": "평점 높은 식당·카페, 노포 비율",
    "gyul": "귤 당도 좋은 동네, 지금 나오는 품종, 근처 시장",
    "hotplace": "사람들이 많이 찾는 관광지",
    "beginner": "제주 처음일 때 가볼 곳 (관광지·오름·해변·식당·시장)",
    "kids": "아이랑 갈 곳 (아이 동반 관광상품, 박물관, 놀이터, 도서관, 소아 진료)",
    "activity": "요트·잠수함·유람선·낚시·카약·돌고래·레일바이크·카트·캠핑·오름·박물관·해수욕·축제 할 수 있는 곳 (question 에 활동 이름)",
    "season": "출발 달별 비용, 빨래 잘 마르는 달, 바람 센 달, 축제 있는 달",
    "safety": "치안·밤길 안전 점수와 근거",
    "contact": "데이터로 답할 수 없는 것(계약·전입·세금·지원금·버스 시간표 등) → 공식 문의처",
}

SYSTEM = """너는 제주살이 동모 '돌몽이'다. 사용자는 지금 돌몽이 웹에서 제주 동네 추천 리포트를 보고 있고,
너는 그 리포트와 연결돼 있어서, 질문에 답하고, 필요하면 조건을 바꿔 다시 계산하고, 리포트 수정을 제안한다.

[반드시 지킬 것]
1. 숫자·장소 이름·출처는 도구 결과에 있는 것만 쓴다. 기억이나 추측으로 만들지 않는다. 도구로 확인 못 한 건 "돌몽이가 모르는 부분이에요"라고 말한다.
   일반 상식으로 "~가 유명해요", "~쪽이 좋아요" 같은 추천을 덧붙이지 않는다. 도구 결과가 주는 문의처·지도 링크로 안내한다.
2. 리포트 요약에 이미 있는 내용이면 도구 없이 답해도 된다. 없는 내용이면 도구를 쓴다.
3. 생활 정보(병원·숙소·맛집·빨래방·아이·활동·시기·치안·예산 절감 등)는 ask_data 로 가져온다. 결과의 링크 [이름](url) 는 그대로 살려서 쓴다.
4. 동네 비교는 compare_regions, 조건을 바꾼 결과가 궁금하면 rank_regions 나 estimate_cost 에 changes 를 넣어 계산한다.
5. 리포트 수정은 직접 하지 않고 propose_report_change 로 '제안'한다. 화면에 [적용하기] 버튼이 뜨고 사용자가 누를 때만 바뀐다.
   - 제안할 때: 대화에서 사용자 조건이 리포트와 달라졌을 때(아이 동반, 차 없음, 기간·예산·인원·출발 달, 중요하게 여기는 것),
     사용자가 바꿔 달라고 했을 때, 또는 계산해 보니 다른 동네가 사용자에게 더 맞을 때(select_region_id).
   - 먼저 rank_regions 등으로 계산해 차이를 확인한 뒤 제안한다. 지금 리포트와 같으면 제안하지 않는다. 한 답에 제안은 한 번.
   - 제안 카드는 사용자가 "네"라고 하기 '전에' 미리 띄우는 것이다. 동의를 기다리지 말고 같은 답 안에서 바로 호출한다.
   - "리포트를 수정해 드릴까요?"라고 물을 거면 반드시 그 전에 propose_report_change 를 호출한다. 호출하지 않았으면 그렇게 묻지 않는다.
   - 호출했으면 답 마지막 줄에 "돌몽이가 ~를 적용해서 리포트를 수정해 드릴까요? 아래 [적용하기]를 눌러 주세요."처럼 묻는다.
   - 단순 궁금증("~면 얼마야?")에는 답만 하고, 그 조건이 사용자 상황 같으면 제안한다.
6. 질문이 여러 가지를 묻으면 도구를 여러 번 써서 다 답한다. 한 번에 여러 도구를 불러도 된다.
7. 말하는 방식: 돌몽이는 공공데이터로 제주를 공부한 친구다. "데이터에서 찾았어요", "데이터에 없어요"라고 하지 말고
   "돌몽이가 아는 낚시터는 ~ 한 곳이에요", "~까지는 돌몽이가 몰라요"처럼 돌몽이가 아는 것과 모르는 것으로 말한다.
   모르는 부분이 있으면 아래 [문의처] 중 관련된 곳을 한 줄로 안내한다. 문의처 목록에 없는 기관·전화번호는 만들지 않는다.
8. 내부 이름은 절대 화면에 쓰지 않는다: 도구 이름, topic 이름(transit, medical 등), region_id(aewol 등), 파일 경로, 영어 변수, 백틱(`).
   동네는 한글 이름으로만 말한다. 다음에 물어볼 만한 걸 제안할 때도 "차 없이 다니는 법도 알려 드릴까요?"처럼 일상어로 쓴다.
9. 사용자가 말하지 않은 조건은 추측해서 바꾸지 않는다. 예: "아이 둘이랑"이면 with_kids 는 바꾸지만, 어른 수를 모르면 인원은 지금 리포트 값을
   그대로 쓰고 답 끝에 "어른은 몇 분이세요?"처럼 한 번만 확인한다.
10. 제주 생활과 상관없는 질문, 데이터로 답할 수 없는 행정·계약 질문은 ask_data(topic=contact) 로 문의처를 안내한다.

[답 쓰는 법]
- 한국어 표준어 해요체로만 쓴다. 문장은 반드시 "~요"로 끝낸다(~어요/~아요/~예요/~이에요/~해요/~세요/~ㄹ게요/~까요/~네요).
  "~다.", "~습니다", "~음", 명사로 끝나는 문장은 쓰지 않는다(목록 항목은 괜찮다). 제주어를 직접 쓰지 않는다 — 서버가 문장 끝 어미를 제주어로 일관되게 바꾼다.
- 친근하지만 짧게: 보통 3~8줄.
- 결론부터 말하고, 근거 숫자를 붙인다. 강조는 **굵게**, 목록은 "- " 만 쓴다. 표·제목(#)·이모지는 쓰지 않는다(화면이 주제에 맞는 돌몽이 아이콘을 따로 붙인다).
- 비용은 '만 원' 단위 추정치라는 걸 필요할 때 한 번만 말한다.
- 출처 목록은 화면이 따로 보여 주니 답 안에 길게 쓰지 않는다.

[문의처] (돌몽이가 모르는 건 여기로 안내)
""" + "\n".join(f"- {c['name']} {c['tel']}" + (f" ({c['hours']})" if c.get("hours") else "") + f": {c['for']}" for c in rule.CONTACTS.values())

# ── 도구 정의 ────────────────────────────────────────────────
TOOLS = [
    {"name": "ask_data",
     "description": "동네 하나의 생활 정보를 우리 공공데이터에서 찾아 사실 문장으로 돌려준다. topic 별 내용:\n"
                    + "\n".join(f"- {k}: {v}" for k, v in TOPICS.items()),
     "input_schema": {"type": "object", "properties": {
         "topic": {"type": "string", "enum": list(TOPICS)},
         "region_id": REGION_ID,
         "question": {"type": "string", "description": "사용자 질문 원문이나 핵심 단어 (시설·활동·목표 금액·다른 동네 이름 등이 들어 있어야 정확해진다)"},
     }, "required": ["topic", "region_id", "question"]}},
    {"name": "rank_regions",
     "description": "조건(지금 리포트 조건 + changes)으로 제주 14개 동네의 비용·점수 순위를 다시 매긴다. "
                    "'차 없이면 어디가 1위야?', '예산 200이면?' 같은 질문에 쓴다. 상위 동네와 예산 초과로 빠진 동네를 돌려준다.",
     "input_schema": {"type": "object", "properties": {"changes": CHANGES_SCHEMA,
                                                       "top_k": {"type": "integer", "description": "기본 5"}}}},
    {"name": "compare_regions",
     "description": "동네 2~4곳을 같은 조건으로 나란히 비교한다 (총비용·항목별 비용·생활 점수·주의 사항·배지).",
     "input_schema": {"type": "object", "properties": {
         "region_ids": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4},
         "changes": CHANGES_SCHEMA}, "required": ["region_ids"]}},
    {"name": "estimate_cost",
     "description": "동네 하나의 체류 비용을 항목별(숙소·렌터카/버스·식비·공과금)로 계산한다. changes 로 조건을 바꿔 볼 수 있다.",
     "input_schema": {"type": "object", "properties": {"region_id": REGION_ID, "changes": CHANGES_SCHEMA},
                      "required": ["region_id"]}},
    {"name": "get_region_detail",
     "description": "동네 하나의 원본 지표(버스 정류장 수, 병원·소아과 수, 응급실 거리, 1월 기온, 혼잡도, 임대지수 등)를 돌려준다.",
     "input_schema": {"type": "object", "properties": {"region_id": REGION_ID}, "required": ["region_id"]}},
    {"name": "rehearse",
     "description": "그 동네에서 평일·주말 하루를 데이터 속 실제 장소로 짜 본 일과표 ('하루 어떻게 보내?', '주말에 뭐 해?').",
     "input_schema": {"type": "object", "properties": {"region_id": REGION_ID}, "required": ["region_id"]}},
    {"name": "propose_report_change",
     "description": "리포트 수정을 사용자에게 제안한다 (바로 바뀌지 않음). 화면에 바뀔 내용과 [적용하기] 버튼이 뜨고, 누르면 조건 입력값이 changes 로 바뀌어 "
                    "순위가 다시 계산되며 select_region_id 동네가 열린다. 사용자 동의를 받기 전에 먼저 호출하는 도구다(카드가 동의를 묻는다). "
                    "다른 도구로 계산한 뒤, 같은 답 안에서 호출한다.",
     "input_schema": {"type": "object", "properties": {
         "changes": CHANGES_SCHEMA,
         "select_region_id": {"type": "string", "description": "리포트에서 열어 줄 동네 (선택)"},
         "reason": {"type": "string", "description": "제안 카드에 보여 줄 한 줄 이유 (예: '차 없이 지낸다고 하셔서 버스·도보로')"}}}},
]
TOOLS[-1]["cache_control"] = {"type": "ephemeral"}  # 시스템 프롬프트 + 도구 정의는 매번 같으니 캐시

TOOL_LABEL = {"ask_data": "데이터 찾기", "rank_regions": "순위 다시 매기기", "compare_regions": "동네 비교",
              "estimate_cost": "비용 계산", "get_region_detail": "동네 지표 보기", "rehearse": "하루 일과 짜기",
              "propose_report_change": "리포트 수정 제안"}
TOPIC_LABEL = {"save": "예산 절감", "car_cost": "렌터카 비용", "priority_cost": "우선순위별 비용", "why": "추천 근거",
               "cons": "단점", "compare": "상위 3곳 장단점", "one_on_one": "1대1 비교", "transit": "교통",
               "amenity": "생활 시설", "medical": "병원·응급실", "lodging": "숙소", "food": "맛집·카페", "gyul": "귤",
               "hotplace": "인기 관광지", "beginner": "처음 가볼 곳", "kids": "아이랑 갈 곳", "activity": "활동",
               "season": "시기", "safety": "치안", "contact": "문의처"}
COND_NAME = {"start_date": "출발", "days": "기간", "people": "인원", "car": "이동", "budget_total": "예산",
             "with_kids": "아이", "remote_work": "원격근무", "with_pet": "반려동물", "prefer_quiet": "조용한 곳",
             "priorities": "중요한 것"}


# ── 도구 실행 ────────────────────────────────────────────────
def _apply(cond: Conditions, changes: dict | None) -> Conditions:
    ok = {k: v for k, v in (changes or {}).items() if k in CHANGES_SCHEMA["properties"]}
    if "priorities" in ok:
        ok["priorities"] = [p for p in ok["priorities"] if p in FACTORS][:3]
    return replace(cond, **ok) if ok else cond


def _rid(region_id: str) -> str:
    """Claude 가 이름('애월')을 넣어도 region_id 로 바꾼다."""
    if region_id in load_regions().index:
        return region_id
    ids = find_region_ids(region_id or "")
    if not ids:
        raise KeyError(f"모르는 동네: {region_id}. 리포트 요약의 region_id 중에서 고르세요.")
    return ids[0]


def _slim(r: dict) -> dict:
    """rank_regions 결과 한 동네 → Claude 에 보낼 만큼만 (전체는 동네당 4KB 라 토큰 낭비)."""
    ls = r["living_scores"]
    return {"region_id": r["region_id"], "name": r["name"], "score": r["score"],
            "total": r["cost"]["total"], "range": r["cost"]["range"], "breakdown": r["cost"]["breakdown"],
            "tier": r["cost"]["tier"],
            "best": [label(k) for k in sorted(ls, key=ls.get, reverse=True)[:2]],
            "worst": [label(k) for k in sorted(ls, key=ls.get)[:2]],
            "badges": r["badges"], "warnings": r["warnings"]}


def _cond_brief(c: dict) -> dict:
    return {k: c.get(k) for k in COND_NAME if c.get(k) not in (None, False, [], "")} | {"car": c.get("car")}


def run_tool(name: str, args: dict, cond: Conditions, ctx: dict) -> dict:
    """도구 하나 실행. ctx 에 출처·리포트 변경을 모은다."""
    if name == "ask_data":
        topic = args["topic"]
        if topic not in rule.HANDLERS or rule.HANDLERS[topic] is None:
            raise KeyError(f"모르는 topic: {topic}")
        rid = _rid(args["region_id"])
        text = args.get("question", "")
        if topic == "activity" and not any(k in text for k in rule.ACTIVITY):
            if not re.search(rule.NO_DATA_ACTIVITY, text):
                text += " 요트"
        if topic == "amenity" and not any(re.search(p, text) for p, _ in rule.AMENITY_WORDS):
            text += " 마트 편의점 빨래방 헬스 약국"
        handler = rule.HANDLERS[topic]
        if topic == "activity" and not any(k in text for k in rule.ACTIVITY):  # 서핑·승마 등 데이터에 없는 활동
            handler = rule.HANDLERS["activity_nodata"]
        lines, sources, nxt = handler(rid, cond, text)
        ctx["sources"] += sources
        ctx["next"] = nxt
        ctx.setdefault("topics", []).append(topic)
        return {"region": get_region_detail(rid)["name"], "facts": lines, "sources": sources}

    if name == "rank_regions":
        c = _apply(cond, args.get("changes"))
        out = rank_regions(c, top_k=int(args.get("top_k") or 5))
        ctx["sources"].append("비용 계산식·추천 점수 (docs/COST_MODEL.md, docs/DATA.md)")
        return {"conditions": _cond_brief(out["conditions"]),
                "weights": {label(k): round(v, 2) for k, v in out["weights"].items()},
                "results": [_slim(r) for r in out["results"]],
                "over_budget": out["over_budget"][:4]}

    if name == "compare_regions":
        c = _apply(cond, args.get("changes"))
        ids = [_rid(x) for x in args["region_ids"]][:4]
        allr = rank_regions(replace(c, budget_total=None), top_k=14)["results"]
        rows = {r["region_id"]: r for r in allr}
        ctx["sources"].append("비용 계산식·추천 점수 (docs/COST_MODEL.md, docs/DATA.md)")
        return {"conditions": _cond_brief(c.to_dict()), "regions": [
            _slim(rows[i]) | {"rank_of_14": [r["region_id"] for r in allr].index(i) + 1,
                              "living_scores": {label(k): v for k, v in rows[i]["living_scores"].items()}}
            for i in ids if i in rows]}

    if name == "estimate_cost":
        c = _apply(cond, args.get("changes"))
        out = estimate_total_cost(_rid(args["region_id"]), c)
        ctx["sources"].append("비용 계산식 docs/COST_MODEL.md")
        return {k: out[k] for k in ("region_name", "tier", "total", "range", "per_month", "breakdown", "alternatives", "assumptions")}

    if name == "get_region_detail":
        d = get_region_detail(_rid(args["region_id"]))
        ctx["sources"].append("제주데이터허브 동네 지표 (docs/DATA.md)")
        return {k: v for k, v in d.items() if v is not None and str(v) != "nan"}

    if name == "rehearse":
        out = rehearse(_rid(args["region_id"]), cond)
        ctx["sources"] += out.get("sources", [])[:3]
        pick = lambda xs: [{k: x[k] for k in ("time", "title", "place")} for x in xs]
        return {"region": out["region_name"], "month": out["month"], "weekday": pick(out["weekday"]),
                "weekend": pick(out["weekend"]), "notes": out["notes"]}

    if name == "propose_report_change":
        c = _apply(cond, args.get("changes"))
        changed = {k: v for k, v in c.to_dict().items() if k in COND_NAME and v != cond.to_dict().get(k)}
        sel = _rid(args["select_region_id"]) if args.get("select_region_id") else None
        ctx["report_update"] = {"conditions": changed, "select_region_id": sel,
                                "reason": args.get("reason") or ", ".join(COND_NAME[k] for k in changed)}
        if not changed and not sel:
            ctx["report_update"] = None
            return {"ok": False, "note": "지금 리포트와 같아서 제안하지 않았다."}
        return {"ok": True, "changed": changed, "select_region_id": sel,
                "note": "제안 카드가 화면에 뜬다. 사용자가 [적용하기]를 눌러야 바뀐다. 답 끝에 적용할지 물어본다."}

    raise KeyError(f"모르는 도구: {name}")


def _trace_label(name: str, args: dict) -> str:
    base = TOOL_LABEL.get(name, name)
    names = load_regions()["name"].to_dict()
    nm = lambda r: names.get(r) or (names.get(find_region_ids(r)[0]) if find_region_ids(r or "") else r)
    if name == "ask_data":
        return f"{base}: {nm(args.get('region_id'))} {TOPIC_LABEL.get(args.get('topic'), args.get('topic'))}"
    if name in ("estimate_cost", "get_region_detail", "rehearse"):
        return f"{base}: {nm(args.get('region_id'))}"
    if name == "compare_regions":
        return f"{base}: " + " vs ".join(nm(r) for r in args.get("region_ids", []))
    ch = args.get("changes") or {}
    if ch:
        return f"{base} ({', '.join(COND_NAME.get(k, k) for k in ch)} 바꿔서)"
    return base


INTERNAL = set(TOPICS) | {t["name"] for t in TOOLS}


def clean_answer(text: str) -> str:
    """내부 이름이 화면에 새지 않게: `transit`(버스·도보) → 버스·도보, 애월읍(aewol) → 애월읍, 남은 백틱 제거."""
    ids = INTERNAL | set(load_regions().index)
    text = re.sub(r"`?\b([a-z][a-z0-9_]*)\b`?\s*\(([^)]+)\)", lambda m: m.group(2) if m.group(1) in ids else m.group(0), text)
    text = re.sub(r"\s*\(\s*`?([a-z][a-z0-9_]*)`?\s*\)", lambda m: "" if m.group(1) in ids else m.group(0), text)
    text = re.sub(r"`([^`]*)`", lambda m: "" if m.group(1) in ids else m.group(1), text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def clean_source(src: str) -> str:
    """참고 데이터 표기에서 파일 경로(docs/...md)와 문서 안 위치 표시를 뺀다."""
    src = re.sub(r"\(?\s*docs/[\w./]+(\s*,\s*docs/[\w./]+)*\s*\)?", "", src)
    src = re.sub(r"\s*→\s*'[^']*'\s*$", "", src)  # "지표 → '추천 점수'" → "지표"
    return src.strip(" ·,→").strip("'").strip() or "돌몽이 비용 계산식"


ASK_APPLY = re.compile(r"리포트[^.?!\n]{0,20}(수정|바꿔|바꾸|적용)[^.?!\n]{0,15}(드릴까요|할까요|드려도)")


# ── 리포트 요약 (Claude 가 '이 동네', '2위' 를 알아듣게) ──────────────────────
def report_context(region_id: str, cond: Conditions) -> str:
    ranked = rank_regions(cond, top_k=14)
    res = ranked["results"]
    here = next((r for r in res if r["region_id"] == region_id), None)
    if here is None:  # 예산 밖 동네를 보고 있으면 예산 없이
        here = next((r for r in rank_regions(replace(cond, budget_total=None), top_k=14)["results"]
                     if r["region_id"] == region_id), None)
    lines = ["[지금 사용자가 보는 리포트]",
             "조건: " + json.dumps(_cond_brief(cond.to_dict()), ensure_ascii=False),
             "추천 순위 (순위. 이름(region_id) 점수, 총비용):"]
    lines += [f"{i}. {r['name']}({r['region_id']}) {r['score']}점, {r['cost']['total']}만 원" for i, r in enumerate(res, 1)]
    if ranked["over_budget"]:
        lines.append("예산 초과로 빠짐: " + ", ".join(f"{o['name']}({o['region_id']}) {o['total']}만 원" for o in ranked["over_budget"]))
    if here:
        lines += [f"지금 열어 본 동네: {here['name']}({here['region_id']})",
                  "  " + json.dumps(_slim(here) | {"indices": {k: v.get("text") for k, v in here["indices"].items()}},
                                    ensure_ascii=False)]
    others = sorted(set(load_regions().index) - {r["region_id"] for r in res} - {o["region_id"] for o in ranked["over_budget"]})
    if others:
        lines.append("그 밖의 동네 id: " + ", ".join(others))
    return "\n".join(lines)


# ── 간단한 사용량 제한 (공개 링크에서 키가 털리지 않게) ─────────────────────────
_HITS: dict[str, list[float]] = {}


def allow(client_id: str) -> bool:
    now = time.time()
    hits = [t for t in _HITS.get(client_id, []) if now - t < 60]
    if len(hits) >= config.AGENT_RATE_PER_MIN:
        _HITS[client_id] = hits
        return False
    _HITS[client_id] = hits + [now]
    return True


def _history(history: list | None) -> list:
    """프론트 대화 기록 → Claude messages (user 로 시작, 역할 번갈아, 최근 8개)."""
    out = []
    for h in (history or [])[-8:]:
        role, text = h.get("role"), str(h.get("content") or "")[:1500]
        if role not in ("user", "assistant") or not text:
            continue
        if out and out[-1]["role"] == role:
            out[-1]["content"] += "\n" + text
        else:
            out.append({"role": role, "content": text})
    while out and out[0]["role"] != "user":
        out.pop(0)
    if out and out[-1]["role"] == "user":
        out.pop()
    return out


def run_agent(message: str, region_id: str, conditions: dict, history: list | None = None, client=None) -> dict:
    """Claude tool-use 루프. client 는 테스트용 가짜를 넣을 수 있다."""
    if client is None:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=config.AGENT_TIMEOUT, max_retries=1)
    cond = Conditions.from_dict(conditions or {})
    region_id = _rid(region_id)
    system = [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}},
              {"type": "text", "text": report_context(region_id, cond)}]
    messages = _history(history) + [{"role": "user", "content": message[:800]}]
    ctx = {"sources": [], "next": None, "report_update": None}
    trace, nudged, resumed = [], False, False

    final_only = False  # True 면 도구 없이 답만 쓰게 한다 (끊긴 답 / 빈 답을 다시 정리할 때)
    for _ in range(config.AGENT_MAX_TURNS + 2):
        kw = {"tool_choice": {"type": "none"}} if final_only else {}
        resp = client.messages.create(model=config.CLAUDE_MODEL, max_tokens=config.AGENT_MAX_TOKENS,
                                      system=system, tools=TOOLS, messages=messages, **kw)
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        # 답이 길이 제한에 걸려 끊겼거나, 도구만 부르고 답을 비워 둔 경우: 한 번만 도구 없이 다시 정리하게 한다
        cut = resp.stop_reason == "max_tokens"
        empty = resp.stop_reason not in ("tool_use", "max_tokens") and not text and trace
        if (cut or empty) and not resumed:
            resumed, final_only = True, True
            if text:
                messages.append({"role": "assistant", "content": [b for b in resp.content if b.type == "text"]})
            messages.append({"role": "user", "content": "(시스템) 답이 끊겼거나 비어 있다. 도구를 더 부르지 말고, 지금까지 받은 도구 결과로 "
                                                       "답 전체를 처음부터 짧게 다시 써라. 목록은 4줄 이내로."})
            continue
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            answer = text
            # 안전장치: "리포트 수정해 드릴까요?"라고 묻고 제안 도구를 안 불렀으면 한 번 더 기회를 준다 (카드가 떠야 적용할 수 있다)
            if ASK_APPLY.search(answer) and ctx["report_update"] is None and not nudged:
                nudged = True
                messages.append({"role": "user", "content": "(시스템) 리포트 수정을 물었는데 propose_report_change 를 호출하지 않아 화면에 [적용하기] 카드가 없다. "
                                                           "지금 호출하고, 답은 처음과 같은 내용으로 다시 써라."})
                continue
            break
        results = []
        for b in resp.content:
            if b.type != "tool_use":
                continue
            try:
                out, err = run_tool(b.name, dict(b.input or {}), cond, ctx), False
            except Exception as e:  # 도구 에러는 Claude 에 돌려줘 스스로 고치게 한다
                out, err = {"error": str(e)}, True
            trace.append({"tool": b.name, "label": _trace_label(b.name, dict(b.input or {})), "error": err})
            results.append({"type": "tool_result", "tool_use_id": b.id, "is_error": err,
                            "content": json.dumps(out, ensure_ascii=False, default=str)})
        messages.append({"role": "user", "content": results})
    else:
        answer = "확인할 게 많아서 정리를 다 못 했어요. 질문을 조금 나눠서 물어봐 주실래요?"

    sources = [clean_source(x) for x in dict.fromkeys(ctx["sources"])][:5]
    answer = strip_emoji(clean_answer(answer)) or "돌몽이가 답을 찾지 못했어요. 제주120만덕콜센터(국번 없이 120)에 물어보세요."
    return {"answer": jeju(answer), "sources": sources, "trace": trace, "icon": pick_icon(message, answer, ctx.get("topics", [])),
            "report_update": ctx["report_update"], "quick_replies": qr_icons(rule._qr(ctx["next"] or [])[:3]),
            "region_id": region_id, "mode": "agent"}
