"""화면에 보이는 숫자마다 '근거'(어떤 데이터의 어떤 값으로 어떻게 계산했는지)를 문장으로 만든다.

심사 기준 '결과 신뢰성': 지표만 보여주지 않고 출처·계산 방식을 같이 보여준다.
문장은 실제 값(row)에서만 만든다. 출처 번호 = 제주데이터허브 데이터 ID (docs/DATA_CATALOG.md).
"""
import pandas as pd

from backend.tools.cost import COST

HUB = "제주데이터허브"


def _n(v, fmt="{:,.0f}"):
    try:
        return fmt.format(float(v)) if pd.notna(v) else "-"
    except (TypeError, ValueError):
        return str(v)


def _place(rank_score: float, n: int = 14) -> str:
    """순위 기반 점수(0~1) → '14곳 중 N위'."""
    pos = round((1 - float(rank_score)) * (n - 1)) + 1
    return f"14곳 중 {pos}위"


# 한 줄 판단 근거: (컬럼, 높을수록 좋은가, 좋을 때 말, 나쁠 때 말)
REASON_PARTS = {
    "교통": [("bus_stops", True, "정류장이 많아요", "정류장이 적어요"), ("bus_routes", True, "다니는 노선이 많아요", "다니는 노선이 적어요")],
    "생활편의": [("amenity_cnt", True, "마트·편의점·카페가 많아요", "마트·편의점·카페가 적어요")],
    "의료": [("hospital_cnt", True, "병·의원이 많아요", "병·의원이 적어요"), ("pediatric_cnt", True, "소아 진료 병원이 많아요", "소아 진료 병원이 적어요"),
             ("er_drive_min", False, "응급실이 가까워요", "응급실이 멀어요")],
    "조용함": [("crowd_index", False, "관광객이 적어요", "관광객이 많이 오가요"), ("rentcar_index", False, "렌터카가 적게 머물러요", "렌터카가 많이 머물러요"),
             ("amenity_cnt", False, "가게가 적은 한적한 동네예요", "가게가 몰린 도심이에요")],
    "자연": [("oreum_cnt", True, "가까운 오름이 많아요", "오름이 적어요"), ("beach_cnt", True, "해변이 가까워요", "해변이 없어요"),
             ("camping_cnt", True, "캠핑장이 많아요", "캠핑장이 적어요")],
    "날씨": [("jan_temp", True, "겨울이 따뜻해요", "겨울이 추운 편이에요"), ("sunshine_jan", True, "겨울 해가 길어요", "겨울 해가 짧아요")],
    "맛집": [("food_top", True, "평점 높은 식당이 많아요", "평점 높은 식당이 적어요"), ("nopo_ratio", True, "오래된 노포가 많아요", "노포가 적어요")],
    "밤길안심": [("cctv_idx", True, "주민 대비 CCTV가 많아요", "주민 대비 CCTV가 적어요"),
               ("police_call_idx", False, "112 신고가 적은 관할이에요", "112 신고가 많은 관할이에요")],
}


def _pct(all_df: pd.DataFrame, col: str, v, higher: bool) -> float | None:
    if all_df is None or col not in all_df or pd.isna(v):
        return None
    vals = pd.to_numeric(all_df[col], errors="coerce").dropna()
    if vals.nunique() < 2:
        return None
    p = (vals < float(v)).mean() + (vals == float(v)).mean() / 2
    return p if higher else 1 - p


def reason(factor: str, row: dict, score: float, all_df: pd.DataFrame | None) -> str:
    """'밤길안심 2/5 — 주민 대비 CCTV가 적어요' 의 뒷부분."""
    parts = [(p, good, bad) for col, hi, good, bad in REASON_PARTS.get(factor, [])
             if (p := _pct(all_df, col, row.get(col), hi)) is not None]
    if not parts:
        return ""
    best = max(parts, key=lambda x: x[0])
    worst = min(parts, key=lambda x: x[0])
    if score >= 0.6:
        return best[1] if best[0] >= 0.5 else "제주 평균보다 나아요"
    if score <= 0.4:
        return worst[2] if worst[0] <= 0.5 else "제주 평균보다 못해요"
    if best[0] >= 0.65 and worst[0] <= 0.35 and best is not worst:
        return f"{best[1]}. 다만 {worst[2]}"
    return "제주 평균 정도예요"


def living_evidence(row: dict, scores: dict, all_df: pd.DataFrame | None = None) -> dict:
    """생활환경 항목별 {how, data}. how = 이 동네 값과 계산, data = 출처."""
    s = scores
    ev = {
        "교통": {
            "how": f"정류장 {_n(row.get('bus_stops'))}곳, 기·종점 노선 {_n(row.get('bus_routes'))}개 → 정류장 60%·노선 40%로 섞어 {_place(s['교통'])}",
            "data": f"{HUB} 612 버스 정류소, 611 버스 노선 (Open API, 2026-11 수집)",
        },
        "생활편의": {
            "how": f"슈퍼마켓·편의점·카페·세탁소 {_n(row.get('amenity_cnt'))}곳 → {_place(s['생활편의'])}",
            "data": f"{HUB} 793 상가(상권) 정보 (2025-09)",
        },
        "의료": {
            "how": f"영업 중 병·의원 {_n(row.get('hospital_cnt'))}곳(40%), 소아 진료 {_n(row.get('pediatric_cnt'))}곳(30%), "
                   f"응급실까지 약 {_n(row.get('er_drive_min'))}분(30%) → {_place(s['의료'])}",
            "data": f"{HUB} 859 병·의원 정보(2025-09), 1046 응급실 보유 병원(2021-08). 응급실 거리는 직선거리×1.3, 시속 45km로 추정",
        },
        "조용함": {
            "how": f"관광객 비율 {_n(row.get('crowd_index'), '{:.2f}')}(25%), 렌터카 습격 {_n(row.get('rentcar_index'), '{:.1f}')}배(20%), "
                   f"상가 수(도심 정도, 40%), 비행기 소음 {('WECPNL ' + _n(row.get('noise_wecpnl'))) if pd.notna(row.get('noise_wecpnl')) else '해당 없음'}(15%) → {_place(s['조용함'])}",
            "data": f"{HUB} 583 읍면동 유동인구(2025-10), 1208 렌터카 체류(2021 하반기), 793 상가정보, 783 항공기 소음(2022)",
        },
        "자연": {
            "how": f"오름 {_n(row.get('oreum_cnt'))}개(50%), 캠핑장 {_n(row.get('camping_cnt'))}곳(25%), 해변 {_n(row.get('beach_cnt'))}곳(25%) → {_place(s['자연'])}",
            "data": f"{HUB} 811 오름 위치, 810 캠핑 장소, 784 해수욕장 정보",
        },
        "날씨": {
            "how": f"{row.get('weather_station')} 관측소 기준. 머무는 달에 겨울이 끼면 1월 평균 {_n(row.get('jan_temp'), '{:.1f}')}℃·일조 {_n(row.get('sunshine_jan'))}시간, "
                   f"아니면 그 달 습도 65% 미만인 날 비율로 → {_place(s['날씨'])}",
            "data": f"{HUB} 877 2000~2021 제주도 일간 기후 (관측소 4곳: 제주·고산·성산·서귀포)",
        },
        "맛집": {
            "how": f"구글 평점 4.5 이상(리뷰 20건↑) 식당 {_n(row.get('food_top'))}곳(60%), 20년 넘은 식당 비율 {_n(float(row.get('nopo_ratio') or 0) * 100)}%(40%) → {_place(s['맛집'])}",
            "data": f"{HUB} 906 구글 음식점 리뷰(2021), 780 음식점 목록(인허가 1960~2025)",
        },
        "밤길안심": {
            "how": f"공공 CCTV {_n(row.get('cctv_cams'))}대(주민 대비 제주 평균의 {_n(row.get('cctv_idx'), '{:.2f}')}배, 70%), "
                   f"{row.get('police_station')} 관할 1인당 112 신고 제주 평균의 {_n(row.get('police_call_idx'), '{:.2f}')}배(적을수록 좋음, 30%) → {_place(s['밤길안심'])}",
            "data": f"{HUB} 846 CCTV 정보(2025-09), 491 제주경찰청 관서별 112신고(2025). 112는 경찰서 3곳 단위라 약하게 반영",
        },
    }
    out = {k: v for k, v in ev.items() if k in scores}
    for k, v in out.items():
        v["reason"] = reason(k, row, float(scores[k]), all_df)
    return out


def cost_evidence(cost: dict, row: dict) -> dict:
    """비용 항목별 {how, data}."""
    cond = cost["conditions"]
    out = {}
    for item in cost["breakdown"]:
        if item == "숙소":
            if cost["tier"] == "연세":
                how = (f"연세 기준 {COST['yearly_rent_base']}만 원 × 임대지수 {row['rent_index']} × 인원 배율 + 초기 세팅비 {COST['yearly_setup_cost']}만 원")
                data = "연세 기준값: 당근부동산 제주시 원룸 연세 평균(2026-11 스냅샷). 임대지수: 국토부 전월세 실거래가"
            else:
                how = (f"권역 월 기준가 {row['base_stay_month']}만 원 × 이 동네 임대지수 {row['rent_index']} × 인원 배율 × 머무는 달의 성수기 배율"
                       f"(7·8월 1.3배, 11월 0.9배 등) × 기간 할인/할증 + 청소비 {COST['cleaning_fee']}만 원")
                data = (f"권역 기준가: jeju.com 2026 한달살이 가이드. 임대지수: 국토부 전월세 실거래가 {_n(row.get('rent_samples'))}건"
                        "(2025-11~2026-10, ㎡당 환산월세 중앙값을 제주 평균과 비교)")
        elif item == "렌터카":
            how = "머무는 날마다 그 달의 렌터카 월 단가 ÷ 30 (1·2월 50만, 3월 40만, 7·8월 100만 원 등)"
            data = "가정값: jeju.com 2026 가이드(표준 월 40~60만), 경향신문 2025-07(성수기 요금이 비수기의 10배 이상)"
        elif item == "버스":
            how = f"1인 월 {COST['bus_month_per_person']}만 원 × {cond['people']}명 × 개월 수"
            data = "가정값 (제주 버스 기본요금 기준 하루 2~3회 이용)"
        elif item == "식비":
            how = f"첫 1명 월 {COST['food_month_first']}만 원 + 추가 1명당 {COST['food_month_extra']}만 원 (취사 위주)"
            data = "가정값: jeju.com 2026 가이드(취사 위주 월 50~70만 원)"
        else:  # 공과금·난방
            how = (f"월 {COST['utility_month']}만 원(단기숙소) 또는 {COST['utility_month_yearly']}만 원(연세) + 12~2월 난방 월 {COST['winter_heating']}만 원"
                   + (f" + 중산간·기름보일러 가능성 {COST['winter_heating_inland']}만 원" if row.get("inland_heating_risk") else ""))
            data = "가정값 (도시가스 공급 범위 데이터가 없어 겨울 가산으로 대신)"
        out[item] = {"how": how, "data": data}
    out["_범위"] = {"how": f"추정 오차 ±{int(COST['range_pct'] * 100)}%를 범위로 보여줘요", "data": "docs/COST_MODEL.md"}
    return out
