"""사용자 조건(Conditions) 정의.

폼 입력과 자연어 입력이 모두 결국 이 구조로 정리된다.
새 조건을 추가하려면:
  1) 아래 dataclass에 필드 추가
  2) backend/agent/mock_parser.py 에 파싱 규칙 추가 (키 없을 때 대비)
  3) backend/tools/registry.py 의 rank_regions input_schema 에 필드 추가 (Claude가 쓰도록)
  4) backend/tools/region.py 의 가중치(_weights)에 반영
"""
from dataclasses import asdict, dataclass, field
from datetime import date


@dataclass
class Conditions:
    start_date: str | None = None      # "YYYY-MM-DD". 없으면 다음 달 1일
    days: int = 30                     # 체류 일수 (7 ~ 365)
    people: int = 1                    # 인원
    car: bool | None = None            # True=렌터카, False=뚜벅이, None=미정(둘 다 계산)
    budget_total: int | None = None    # 총 예산(만원). None이면 필터 안 함
    with_kids: bool = False
    remote_work: bool = False
    with_pet: bool = False             # TODO[DATA]: 반려동물 동반 가능 숙소 데이터 생기면 반영
    prefer_quiet: bool = False
    regions: list[str] = field(default_factory=list)  # 특정 지역만 비교하고 싶을 때 region_id 목록
    # 사용자가 고른 '가장 중요한 것' 최대 3개, 중요한 순서대로. 값은 region.PRIORITY_KEYS
    # (비용·교통·생활편의·의료·조용함·자연·날씨·맛집·밤길안심). 비어 있으면 다른 조건으로 가중치를 추정한다.
    priorities: list[str] = field(default_factory=list)

    def resolved_start(self) -> date:
        if self.start_date:
            return date.fromisoformat(self.start_date)
        today = date.today()
        y, m = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        return date(y, m, 1)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start_date"] = self.resolved_start().isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Conditions":
        allowed = cls.__dataclass_fields__.keys()
        clean = {k: v for k, v in (d or {}).items() if k in allowed and v is not None}
        c = cls(**clean)
        c.days = max(1, min(int(c.days), 730))
        c.people = max(1, min(int(c.people), 10))
        c.priorities = [p for p in dict.fromkeys(c.priorities or []) if isinstance(p, str)][:3]
        return c
