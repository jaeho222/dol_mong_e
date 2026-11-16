"""Agent 도구 등록소 — 도구를 추가할 곳은 여기 한 군데.

Claude Agent와 Mock Agent가 모두 이 목록을 사용한다.

새 도구 추가 3단계:
  1) backend/tools/ 아래에 순수 파이썬 함수를 만든다 (dict 입력 → JSON 직렬화 가능한 dict 출력)
  2) 아래 TOOLS 에 Tool(...) 을 하나 추가한다 (name, description, input_schema, fn)
     - description 은 Claude가 '언제 이 도구를 쓸지' 판단하는 근거이니 구체적으로!
  3) tests/test_tools.py 에 간단한 테스트를 추가한다
"""
from dataclasses import dataclass
from typing import Any, Callable

from backend.tools.cost import estimate_total_cost
from backend.tools.region import get_region_detail, list_regions, rank_regions

CONDITIONS_SCHEMA = {
    "type": "object",
    "description": "사용자 조건. 언급되지 않은 값은 생략한다.",
    "properties": {
        "start_date": {"type": "string", "description": "입도 날짜 YYYY-MM-DD. 월만 언급되면 그 달 1일"},
        "days": {"type": "integer", "description": "체류 일수. 한 달=30, 3개월=90, 1년=365"},
        "people": {"type": "integer", "description": "인원 수"},
        "car": {"type": "boolean", "description": "렌터카 사용 여부. 차 없이(뚜벅이)면 false. 모르면 생략"},
        "budget_total": {"type": "integer", "description": "체류 전체 총예산(만원). '월 200'이면 200×개월수로 환산"},
        "with_kids": {"type": "boolean"},
        "remote_work": {"type": "boolean", "description": "원격근무·워케이션 여부"},
        "with_pet": {"type": "boolean"},
        "prefer_quiet": {"type": "boolean", "description": "조용한 동네 선호"},
        "regions": {"type": "array", "items": {"type": "string"},
                    "description": "특정 지역만 비교할 때 region_id 목록 (list_regions로 확인)"},
    },
}


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    fn: Callable[..., Any]

    def run(self, args: dict) -> Any:
        return self.fn(**args)

    def to_anthropic(self) -> dict:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


TOOLS: list[Tool] = [
    Tool(
        name="list_regions",
        description="비교 가능한 제주 지역 목록(region_id, 이름, 권역)을 돌려준다. 사용자가 말한 지역명을 region_id로 바꿀 때 사용.",
        input_schema={"type": "object", "properties": {}},
        fn=lambda: list_regions(),
    ),
    Tool(
        name="rank_regions",
        description=(
            "사용자 조건으로 모든(또는 지정한) 지역의 체류 총비용을 추정하고, 비용과 생활환경 점수를 합쳐 "
            "추천 순위를 매긴다. 지역 추천·비교 질문에는 거의 항상 이 도구를 먼저 호출한다."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "conditions": CONDITIONS_SCHEMA,
                "top_k": {"type": "integer", "description": "돌려받을 지역 수 (기본 5)"},
            },
            "required": ["conditions"],
        },
        fn=lambda conditions, top_k=5: rank_regions(conditions, top_k=top_k),
    ),
    Tool(
        name="estimate_total_cost",
        description="특정 지역 하나의 체류 총비용을 항목별(숙소·이동·식비·공과금)로 추정한다. '애월이면 얼마야?' 같은 질문에 사용.",
        input_schema={
            "type": "object",
            "properties": {"region_id": {"type": "string"}, "conditions": CONDITIONS_SCHEMA},
            "required": ["region_id", "conditions"],
        },
        fn=lambda region_id, conditions: estimate_total_cost(region_id, conditions),
    ),
    Tool(
        name="get_region_detail",
        description="지역 하나의 원본 지표(버스 정류장 수, 병원 수, 1월 기온, 혼잡도 등)를 돌려준다. 근거를 설명할 때 사용.",
        input_schema={"type": "object", "properties": {"region_id": {"type": "string"}}, "required": ["region_id"]},
        fn=lambda region_id: get_region_detail(region_id),
    ),
    # TODO[AGENT]: 예) compare_stay_length — 같은 지역에서 1/3/6/12개월 비용 비교 도구
    # TODO[AGENT]: 예) get_support_programs — 한달살기 지원금·워케이션 바우처 안내 도구
]

TOOLS_BY_NAME = {t.name: t for t in TOOLS}
