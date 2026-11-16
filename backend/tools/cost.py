"""체류 총비용 추정 도구.

⚠️ 모든 단가는 현재 '가정값'이다. (출처: 리서치 리포트의 권역 가격대·기사 수치)
   TODO[DATA]: COST 상수를 실제 데이터로 보정하고, 근거를 docs/COST_MODEL.md 에 적을 것.

계산 흐름
  1. 기간에 따라 숙소 형태 결정 (단기숙소 / 연세) — 90일 이상이면 둘 다 계산해 싼 쪽 선택
  2. 하루 단위로 돌며 '그 날짜가 속한 월'의 성수기 배율을 적용
  3. 렌터카(또는 버스), 식비, 공과금(겨울 난방 가산)을 더함
  4. 추정 오차 범위(±RANGE_PCT)와 가정 목록을 같이 반환 → UI가 '추정'으로 표시
"""
from datetime import date, timedelta

from backend.schema import Conditions
from backend.tools.data_loader import get_region

# 단위: 만원
COST = {
    # 숙소 성수기 배율 (월별)
    "season_mult": {1: 1.10, 2: 1.10, 3: 0.95, 4: 1.0, 5: 1.0, 6: 1.0,
                    7: 1.30, 8: 1.30, 9: 1.0, 10: 1.05, 11: 0.90, 12: 1.10},
    # 체류 길이 할인/할증 (일수 상한, 배율)
    "length_mult": [(13, 1.25), (27, 1.10), (89, 1.00), (180, 0.88), (10_000, 0.80)],
    # 인원에 따른 숙소 규모 배율
    "size_mult": {1: 1.0, 2: 1.15, 3: 1.35, 4: 1.45},
    "cleaning_fee": 5,
    # 연세(1년 선불) 기준값 — 당근부동산 제주시 원룸 연세 평균(2026-11 스냅샷)
    "yearly_rent_base": 639,
    "yearly_deposit_base": 247,
    "yearly_setup_cost": 50,          # 가구·가전·이사 초기비용 가정
    # 렌터카 월 단가 (월별)
    "car_month": {1: 50, 2: 50, 3: 40, 4: 45, 5: 45, 6: 50,
                  7: 100, 8: 100, 9: 45, 10: 45, 11: 40, 12: 50},
    "bus_month_per_person": 6,
    "food_month_first": 60,           # 1인 취사 위주
    "food_month_extra": 50,           # 추가 인원 1명당
    "utility_month": 8,               # 단기숙소: 공과금 별도인 경우 대비 버퍼
    "utility_month_yearly": 15,       # 연세: 공과금 직접 부담
    "winter_heating": 10,             # 12~2월 추가 난방비
    "winter_heating_inland": 10,      # 중산간·기름보일러 추가
    "range_pct": 0.15,
}


def _length_mult(days: int) -> float:
    for limit, mult in COST["length_mult"]:
        if days <= limit:
            return mult
    return 1.0


def _size_mult(people: int) -> float:
    return COST["size_mult"].get(people, COST["size_mult"][4] + 0.1 * (people - 4))


def _iter_days(start: date, days: int):
    for i in range(days):
        yield start + timedelta(days=i)


def _short_term_lodging(region: dict, cond: Conditions, start: date) -> float:
    monthly = region["base_stay_month"] * region["rent_index"] * _size_mult(cond.people)
    daily = monthly / 30
    total = sum(daily * COST["season_mult"][d.month] for d in _iter_days(start, cond.days))
    return total * _length_mult(cond.days) + COST["cleaning_fee"]


def _yearly_lodging(region: dict, cond: Conditions) -> float:
    years = -(-cond.days // 365)  # 올림: 연세는 1년 단위로 낸다
    yearly = COST["yearly_rent_base"] * region["rent_index"] * _size_mult(cond.people)
    return yearly * years + COST["yearly_setup_cost"]


def estimate_total_cost(region_id: str, conditions: dict | Conditions) -> dict:
    cond = conditions if isinstance(conditions, Conditions) else Conditions.from_dict(conditions)
    region = get_region(region_id)
    start = cond.resolved_start()
    months = cond.days / 30
    assumptions = []

    # 1) 숙소
    short = _short_term_lodging(region, cond, start)
    lodging, tier, alternatives = short, "단기숙소", []
    if cond.days >= 90:
        yearly = _yearly_lodging(region, cond)
        alt = {"tier": "연세", "lodging": round(yearly)} if yearly >= short else {"tier": "단기숙소", "lodging": round(short)}
        if yearly < short:
            lodging, tier = yearly, "연세"
            assumptions.append(
                f"연세는 1년치 선불 + 보증금 약 {round(COST['yearly_deposit_base'] * region['rent_index'])}만원(반환형, 총액 미포함)"
            )
        alternatives.append(alt)

    # 2) 이동
    if cond.car is False:
        transport = COST["bus_month_per_person"] * cond.people * months
        transport_label = "버스"
    else:
        transport = sum(COST["car_month"][d.month] / 30 for d in _iter_days(start, cond.days))
        transport_label = "렌터카"
        if cond.car is None:
            assumptions.append("차량 여부 미정 → 렌터카 기준으로 계산")

    # 3) 식비
    food = (COST["food_month_first"] + COST["food_month_extra"] * (cond.people - 1)) * months

    # 4) 공과금·난방
    util_base = COST["utility_month_yearly"] if tier == "연세" else COST["utility_month"]
    utilities = util_base * months
    winter_days = sum(1 for d in _iter_days(start, cond.days) if d.month in (12, 1, 2))
    if winter_days:
        heat = COST["winter_heating"] + (COST["winter_heating_inland"] if region["inland_heating_risk"] else 0)
        utilities += heat * winter_days / 30
        assumptions.append("겨울 난방비 가산" + (" (중산간/기름보일러 가능성)" if region["inland_heating_risk"] else ""))

    breakdown = {
        "숙소": round(lodging),
        transport_label: round(transport),
        "식비": round(food),
        "공과금·난방": round(utilities),
    }
    total = sum(breakdown.values())
    r = COST["range_pct"]
    assumptions.insert(0, "모든 단가는 추정값입니다 (docs/COST_MODEL.md)")
    if region.get("is_dummy"):
        assumptions.insert(0, "⚠️ 지역 지표가 아직 더미 데이터입니다")

    return {
        "region_id": region_id,
        "region_name": region["name"],
        "tier": tier,
        "total": total,
        "range": [round(total * (1 - r)), round(total * (1 + r))],
        "per_month": round(total / max(months, 1 / 30)),
        "breakdown": breakdown,
        "alternatives": alternatives,
        "assumptions": assumptions,
        "conditions": cond.to_dict(),
        "unit": "만원",
    }
