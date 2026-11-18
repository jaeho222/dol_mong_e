"""지역 비교·추천 도구.

점수 = 항목별 점수(0~1)의 가중평균. 항목 = 비용 + 생활환경 8가지(FACTORS).
가중치:
  - 사용자가 '가장 중요한 것 3가지'(Conditions.priorities)를 고르면 고른 순서대로 3·2·1, 나머지 0.3
  - 안 고르면 예전처럼 조건에서 추정: 비용 = 생활환경 합과 같은 비중(50:50), 차 없음 → 교통 ×3,
    아이 → 의료 ×3, 겨울 체류 → 날씨 ×2, 조용한 곳 → 조용함 ×2
점수 매기는 법:
  - 생활환경: 14개 권역 안의 순위 기반 0~1 (원도심처럼 한 곳이 튀어도 나머지가 0 근처로 눌리지 않게)
  - 비용: 가장 싼 동네 대비 몇 % 비싼지로 (50% 비싸면 0점). 실제 차이가 작으면 점수 차이도 작다

새 생활환경 항목을 추가하려면:
  1) region_metrics.csv 에 컬럼 추가 (supabase/sql → export)
  2) FACTORS 에 (점수명: 계산 함수) 추가, 화면 라벨은 frontend config.js 의 priorities·traits
"""
import pandas as pd

from backend.schema import Conditions
from backend.tools.cost import estimate_total_cost
from backend.tools.data_loader import get_region, load_regions
from backend.tools.evidence import cost_evidence, living_evidence
from backend.tools.indices import region_indices, stay_months, _weather

COST_ZERO_AT = 0.5   # 가장 싼 동네보다 50% 비싸면 비용 점수 0


def _norm(s: pd.Series, invert: bool = False) -> pd.Series:
    lo, hi = s.min(), s.max()
    out = (s - lo) / (hi - lo) if hi > lo else s * 0 + 0.5
    return 1 - out if invert else out


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


def _col(df: pd.DataFrame, c: str, default: float = 0.0) -> pd.Series:
    return df[c].astype(float).fillna(default) if c in df.columns else pd.Series(default, index=df.index)


def _weather_score(df: pd.DataFrame, cond: Conditions) -> pd.Series:
    """머무는 달 기준: 겨울(11~2월)이 끼면 1월 기온·일조, 아니면 그 달 빨래 마르는 날 비율."""
    months = stay_months(cond)
    if set(months) & {11, 12, 1, 2}:
        return 0.5 * _rank(_col(df, "jan_temp")) + 0.5 * _rank(_col(df, "sunshine_jan"))
    w = _weather()
    if w is None or "weather_station" not in df.columns:
        return _rank(_col(df, "jan_temp"))
    share = w[w["month"].isin(months)].groupby("station")["laundry_share"].mean()
    return _rank(df["weather_station"].map(share).fillna(share.mean()))


# 생활환경 항목: (df, cond) → 0~1 Series. 사용자가 고르는 선택지 키와 같다.
FACTORS = {
    "교통": lambda df, c: 0.6 * _rank(_col(df, "bus_stops")) + 0.4 * _rank(_col(df, "bus_routes")),
    "생활편의": lambda df, c: _rank(_col(df, "amenity_cnt")),
    "의료": lambda df, c: 0.4 * _rank(_col(df, "hospital_cnt")) + 0.3 * _rank(_col(df, "pediatric_cnt"))
    + 0.3 * _rank(-_col(df, "er_drive_min", 60)),
    # 관광객 비율(583) + 렌터카 습격(1208) + 도심 정도(상가 수, 793) + 비행기 소음(783, 75 이상만 감점)
    # 관광객 비율만 보면 원도심처럼 '관광객은 적지만 번화한' 곳이 조용하게 나와서 도심 정도를 넣었다
    "조용함": lambda df, c: 0.25 * _rank(-_col(df, "crowd_index")) + 0.2 * _rank(-_col(df, "rentcar_index", 1))
    + 0.4 * _rank(-_col(df, "amenity_cnt")) + 0.15 * (_col(df, "noise_wecpnl") < 75).astype(float),
    # 오름(811) + 캠핑장(810) + 해변(784)
    "자연": lambda df, c: 0.5 * _rank(_col(df, "oreum_cnt")) + 0.25 * _rank(_col(df, "camping_cnt"))
    + 0.25 * _rank(_col(df, "beach_cnt")),
    "날씨": _weather_score,
    # 구글 평점 4.5↑ 식당 수(906×780) + 노포 비율(780)
    "맛집": lambda df, c: 0.6 * _rank(_col(df, "food_top")) + 0.4 * _rank(_col(df, "nopo_ratio")),
    # 거주자당 공공 CCTV(846) 0.7 + 경찰서 관할 1인당 112 신고(491, 3개 관할뿐이라 약하게) 0.3
    "밤길안심": lambda df, c: 0.7 * _rank(_col(df, "cctv_idx")) + 0.3 * _rank(-_col(df, "police_call_idx", 1)),
}
# 화면·Agent 가 쓰는 선택지 (비용 포함). 원격근무는 와이파이·공유오피스가 아직 수동값이라 뺐다.
PRIORITY_KEYS = ["비용", *FACTORS.keys()]
PRIORITY_WEIGHTS = (3.0, 2.0, 1.0)
UNCHOSEN_WEIGHT = 0.3


def _weights(cond: Conditions) -> dict:
    """항목별 가중치 (비용 포함)."""
    chosen = [p for p in (cond.priorities or []) if p in PRIORITY_KEYS][:3]
    if chosen:
        w = {k: UNCHOSEN_WEIGHT for k in PRIORITY_KEYS}
        for k, v in zip(chosen, PRIORITY_WEIGHTS):
            w[k] = v
        return w
    w = {k: 1.0 for k in FACTORS}
    if cond.car is False:
        w["교통"] = 3.0
    if cond.with_kids:
        w["의료"] = 3.0
    start = cond.resolved_start()
    if start.month in (11, 12, 1, 2) or (start.month == 10 and cond.days > 45):
        w["날씨"] = 2.0
    if cond.prefer_quiet:
        w["조용함"] = 2.0
    w["비용"] = sum(w.values())   # 비용 : 생활환경 = 50 : 50
    return w


def _badges(row: dict, scores: dict, cond: Conditions, w: dict) -> tuple[list[str], list[str]]:
    good, warn = [], []
    winter = bool(set(stay_months(cond)) & {11, 12, 1, 2})
    if scores["교통"] >= 0.6:
        good.append("차 없어도 괜찮아요")
    elif cond.car is False and scores["교통"] < 0.3:
        warn.append("버스가 드물어요")
    if winter and scores["날씨"] >= 0.7:
        good.append("겨울이 따뜻해요")
    if row["pediatric_cnt"] > 0 and cond.with_kids:
        good.append("소아과 있어요")
    if row["er_drive_min"] >= 40:
        warn.append(f"응급실까지 {int(row['er_drive_min'])}분")
    if scores["조용함"] >= 0.7:
        good.append("조용한 동네예요")
    if row["cowork_cnt"] >= 2 and cond.remote_work:
        good.append("공유오피스 있어요")
    if row["odor_flag"]:
        warn.append("축산 악취 민원 지역")
    if winter and row["snow_road_flag"]:
        warn.append("폭설 땐 산간도로 통제")
    return good, warn


def rank_regions(conditions: dict | Conditions, top_k: int = 5) -> dict:
    cond = conditions if isinstance(conditions, Conditions) else Conditions.from_dict(conditions)
    df = load_regions()
    all_regions = df
    # 점수 정규화는 '제주 전체' 기준으로 해야 일부 지역만 비교해도 의미가 유지된다
    scores = pd.DataFrame({k: f(df, cond) for k, f in FACTORS.items()})
    fun = fun_scores(df)
    if cond.regions:
        df = df[df["region_id"].isin(cond.regions)]
        scores = scores.loc[df.index]
        fun = fun.loc[df.index]
    w = _weights(cond)

    costs = {rid: estimate_total_cost(rid, cond) for rid in df.index}
    total_series = pd.Series({rid: c["total"] for rid, c in costs.items()})
    # 가장 싼 동네 대비 % 차이로 (전체 14곳 기준이 아니라 비교 대상 안에서)
    cost_score = (1 - (total_series / total_series.min() - 1) / COST_ZERO_AT).clip(0, 1)
    all_scores = scores.assign(비용=cost_score)
    final = sum(all_scores[k] * w[k] for k in w) / sum(w.values())

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
            "cost_score": round(float(cost_score[rid]), 2),
            "fun_scores": fun.loc[rid].round(2).to_dict() if not fun.empty else {},
            # 눈에 띄는 동네 지수만 (임계값 못 넘으면 빠짐) — backend/tools/indices.py
            "indices": region_indices(row, all_regions, cond),
            # 화면의 '?'·'산정방식 보기'에 쓰는 근거 문장 (backend/tools/evidence.py)
            "evidence": {"living": living_evidence(row, scores.loc[rid].to_dict(), all_regions),
                         "cost": cost_evidence(costs[rid], row),
                         "weights": {k: round(v, 2) for k, v in w.items()}},
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
            ({"region_id": i["region_id"], "name": i["name"], "total": i["cost"]["total"], "score": i["score"],
              "over": i["cost"]["total"] - cond.budget_total} for i in over_budget),
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
