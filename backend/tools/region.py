"""지역 비교·추천 도구.

점수 = 비용 점수(cost_weight) + 생활환경 점수(나머지)
생활환경 항목별 가중치는 사용자 조건에 따라 바뀐다 (_weights).
  - 차 없음 → 교통 ×3
  - 아이 동반 → 의료 ×3
  - 원격근무 → 원격근무 ×3
  - 겨울 체류 → 겨울 날씨 ×2
  - 조용한 곳 선호 → 한적함 ×2

새 생활환경 지표를 추가하려면:
  1) region_metrics.csv 에 컬럼 추가 (data_loader.REQUIRED_COLUMNS 에도)
  2) LIVING_METRICS 에 (점수명, 계산 함수) 추가
  3) 필요하면 _weights / _badges 에 규칙 추가
"""
import pandas as pd

from backend.schema import Conditions
from backend.tools.cost import estimate_total_cost
from backend.tools.data_loader import get_region, load_regions
from backend.tools.indices import region_indices


def _norm(s: pd.Series, invert: bool = False) -> pd.Series:
    lo, hi = s.min(), s.max()
    out = (s - lo) / (hi - lo) if hi > lo else s * 0 + 0.5
    return 1 - out if invert else out


# 점수명 → df를 받아 0~1 Series를 돌려주는 함수
LIVING_METRICS = {
    "교통": lambda df: 0.6 * _norm(df["bus_stops"]) + 0.4 * _norm(df["bus_routes"]),
    "생활편의": lambda df: _norm(df["amenity_cnt"]),
    "의료": lambda df: 0.4 * _norm(df["hospital_cnt"]) + 0.3 * _norm(df["pediatric_cnt"])
    + 0.3 * _norm(df["er_drive_min"], invert=True),
    "겨울날씨": lambda df: 0.5 * _norm(df["jan_temp"]) + 0.5 * _norm(df["sunshine_jan"]),
    # 거주 인구 대비 방문 인구 비율이 낮을수록 높음 (관광객이 덜 붐비는 정도)
    "한적함": lambda df: _norm(df["crowd_index"], invert=True),
    "원격근무": lambda df: 0.5 * _norm(df["wifi_ap"]) + 0.5 * _norm(df["cowork_cnt"]),
}


def _rank(s: pd.Series) -> pd.Series:
    """순위 기반 0~1 (제일 낮은 곳 0, 제일 높은 곳 1). 값 하나가 튀어도 나머지가 한쪽에 몰리지 않는다."""
    if len(s) < 2:
        return s * 0 + 0.5
    return (s.rank(method="average") - 1) / (len(s) - 1)


# 재미 지수: 추천 순위에는 넣지 않고 결과에 따로 붙인다 (0~1, 높을수록 그 성격이 강함).
# 계산 근거·교차검증은 docs/DATA.md '재미 지수'. 컬럼이 없는 CSV(sample)면 건너뛴다.
FUN_INDICES = {
    # 거주 인구당 렌터카 체류 지점 수(제주 평균=1). 원값은 인구 규모를 따라가서(r=0.87) 쓰지 않음
    "렌터카습격": ("rentcar_index", lambda df: _rank(df["rentcar_index"])),
    # 지번주소 기준 권역 내 오름 개수
    "오름부자": ("oreum_cnt", lambda df: _rank(df["oreum_cnt"])),
    # 영업 중 음식점 중 20년 이상(2006년 이전 인허가) 비율
    "노포": ("nopo_ratio", lambda df: _rank(df["nopo_ratio"])),
    # 2021~2023 신생 사업체 ÷ 활동 사업체
    "요즘뜨는": ("new_biz_rate", lambda df: _rank(df["new_biz_rate"])),
}


def fun_scores(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({k: f(df) for k, (col, f) in FUN_INDICES.items() if col in df.columns}, index=df.index)


def _weights(cond: Conditions) -> dict:
    w = {k: 1.0 for k in LIVING_METRICS}
    if cond.car is False:
        w["교통"] = 3.0
    if cond.with_kids:
        w["의료"] = 3.0
    if cond.remote_work:
        w["원격근무"] = 3.0
    start = cond.resolved_start()
    if start.month in (11, 12, 1, 2) or (start.month == 10 and cond.days > 45):
        w["겨울날씨"] = 2.0
    if cond.prefer_quiet:
        w["한적함"] = 2.0
    return w


def _badges(row: dict, scores: dict, cond: Conditions, w: dict) -> tuple[list[str], list[str]]:
    good, warn = [], []
    winter = w["겨울날씨"] > 1
    if scores["교통"] >= 0.6:
        good.append("차 없어도 괜찮아요")
    elif cond.car is False and scores["교통"] < 0.3:
        warn.append("버스가 드물어요")
    if winter and scores["겨울날씨"] >= 0.7:
        good.append("겨울이 따뜻해요")
    if row["pediatric_cnt"] > 0 and cond.with_kids:
        good.append("소아과 있어요")
    if row["er_drive_min"] >= 40:
        warn.append(f"응급실까지 {int(row['er_drive_min'])}분")
    if scores["한적함"] >= 0.7:
        good.append("관광객이 적어요")
    if row["cowork_cnt"] >= 2 and cond.remote_work:
        good.append("공유오피스 있어요")
    if row["odor_flag"]:
        warn.append("축산 악취 민원 지역")
    if winter and row["snow_road_flag"]:
        warn.append("폭설 땐 산간도로 통제")
    return good, warn


def rank_regions(conditions: dict | Conditions, top_k: int = 5, cost_weight: float = 0.5) -> dict:
    cond = conditions if isinstance(conditions, Conditions) else Conditions.from_dict(conditions)
    df = load_regions()
    all_regions = df
    # 점수 정규화는 '제주 전체' 기준으로 해야 일부 지역만 비교해도 의미가 유지된다
    scores = pd.DataFrame({k: f(df) for k, f in LIVING_METRICS.items()})
    fun = fun_scores(df)
    if cond.regions:
        df = df[df["region_id"].isin(cond.regions)]
        scores = scores.loc[df.index]
        fun = fun.loc[df.index]
    w = _weights(cond)
    living = sum(scores[k] * w[k] for k in w) / sum(w.values())

    costs = {rid: estimate_total_cost(rid, cond) for rid in df.index}
    total_series = pd.Series({rid: c["total"] for rid, c in costs.items()})
    cost_score = _norm(total_series, invert=True)
    final = cost_weight * cost_score + (1 - cost_weight) * living

    items, over_budget = [], []
    for rid in final.sort_values(ascending=False).index:
        row = df.loc[rid].to_dict()
        sc = scores.loc[rid].round(2).to_dict()
        good, warn = _badges(row, sc, cond, w)
        item = {
            "region_id": rid,
            "name": row["name"],
            "zone": row["zone"],
            "lat": row["lat"],
            "lon": row["lon"],
            "score": round(float(final[rid]) * 100),
            "living_scores": sc,
            "fun_scores": fun.loc[rid].round(2).to_dict() if not fun.empty else {},
            # 눈에 띄는 동네 지수만 (임계값 못 넘으면 빠짐) — backend/tools/indices.py
            "indices": region_indices(row, all_regions, cond),
            "cost": costs[rid],
            "badges": good,
            "warnings": warn,
        }
        if cond.budget_total and costs[rid]["total"] > cond.budget_total:
            over_budget.append(item)
        else:
            items.append(item)

    return {
        "conditions": cond.to_dict(),
        "weights": w,
        "results": items[:top_k],
        "over_budget": sorted(
            ({"region_id": i["region_id"], "name": i["name"], "total": i["cost"]["total"]} for i in over_budget),
            key=lambda x: x["total"],
        ),
        "unit": "만원",
    }


def get_region_detail(region_id: str) -> dict:
    row = get_region(region_id)
    return {k: (v.item() if hasattr(v, "item") else v) for k, v in row.items()}


def list_regions() -> list[dict]:
    df = load_regions()
    return df[["region_id", "name", "city", "zone", "lat", "lon"]].to_dict(orient="records")
