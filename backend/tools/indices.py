"""동네 지수: '보여줄 만한 차이'가 있을 때만 결과에 넣는다.

각 지수는 (그 동네 값, 비교 기준, 임계값)으로 판단한다.
  - 계절 지수(빨래·산발·귤)는 사용자가 머무는 달만 본다.
  - 동네 성격 지수(렌터카·노포·오름·요즘 뜨는)는 14개 권역 안에서의 위치(순위)로 본다.
임계값을 못 넘으면 그 지수는 빠진다 → 화면에는 눈에 띄는 것만 뜬다.

반환: {key: {"value": 짧은 수치 문자열, "text": 돌몽이 한마디, "tone": "good"|"warn"|"info", "score": 0~100}}
근거·교차검증: docs/DATA.md '재미 지수'
"""
from datetime import timedelta
from functools import lru_cache

import pandas as pd

from backend import config
from backend.schema import Conditions

PROCESSED = config.ROOT_DIR / "data" / "processed"

# ── 임계값 (바꾸면 docs/DATA.md 표도 같이) ─────────────────────────
LAUNDRY_DIFF = 0.08      # 빨래: 제주 평균보다 '마르는 날' 비율이 8%p 이상 차이
HAIR_MIN = 0.15          # 산발: 강풍(최대풍속 10m/s↑) 부는 날이 15% 이상이면서
HAIR_DIFF = 0.10         #       제주 평균보다 10%p 이상 많을 때
RENTCAR_HIGH = 1.5       # 렌터카: 거주자당 렌터카 체류가 제주 평균의 1.5배 이상
RENTCAR_LOW = 0.7        #         0.7배 이하면 '조용함'으로 표시
TOP_RANK = 0.75          # 노포·오름·요즘 뜨는: 14개 권역 중 상위 25%
GYUL_PEAK = 0.30         # 귤: 머무는 달에 그 품종 연간 출하의 30% 이상이 몰릴 때


@lru_cache(maxsize=1)
def _weather() -> pd.DataFrame | None:
    p = PROCESSED / "weather_month.csv"
    return pd.read_csv(p) if p.exists() else None


@lru_cache(maxsize=1)
def _gyul() -> pd.DataFrame | None:
    p = PROCESSED / "gyul_month.csv"
    return pd.read_csv(p) if p.exists() else None


def stay_months(cond: Conditions) -> list[int]:
    start = cond.resolved_start()
    months = []
    for i in range(max(cond.days, 1)):
        m = (start + timedelta(days=i)).month
        if m not in months:
            months.append(m)
    return months


def _rank(s: pd.Series) -> pd.Series:
    return (s.rank(method="average") - 1) / max(len(s) - 1, 1)


def region_indices(row: dict, all_regions: pd.DataFrame, cond: Conditions) -> dict:
    out: dict = {}
    months = stay_months(cond)
    mtxt = f"{months[0]}월" if len(months) == 1 else f"{months[0]}~{months[-1]}월"

    # 빨래 / 산발 — 그 동네가 붙는 관측소의 머무는 달 평균 vs 4개 관측소 평균
    w = _weather()
    st = row.get("weather_station")
    if w is not None and isinstance(st, str):
        wm = w[w["month"].isin(months)]
        mine = wm[wm["station"] == st]
        if not mine.empty:
            lau, lau_avg = mine["laundry_share"].mean(), wm["laundry_share"].mean()
            if lau - lau_avg >= LAUNDRY_DIFF:
                out["laundry"] = {"value": f"{lau:.0%}", "tone": "good", "score": round(lau * 100),
                                  "text": f"{mtxt}엔 빨래 잘 마르는 날이 {lau:.0%}예요. 제주 평균보다 {lau - lau_avg:.0%}p 많아요."}
            elif lau_avg - lau >= LAUNDRY_DIFF:
                out["laundry"] = {"value": f"{lau:.0%}", "tone": "warn", "score": round(lau * 100),
                                  "text": f"{mtxt}엔 습한 날이 많아 빨래가 잘 안 말라요(마르는 날 {lau:.0%}, 제주 평균 {lau_avg:.0%})."}
            hair, hair_avg = mine["windy_share"].mean(), wm["windy_share"].mean()
            if hair >= HAIR_MIN and hair - hair_avg >= HAIR_DIFF:
                out["hair"] = {"value": f"{hair:.0%}", "tone": "warn", "score": round(hair * 100),
                               "text": f"{mtxt}엔 강풍 부는 날이 {hair:.0%}예요. 머리 묶을 끈 챙기세요."}

    # 렌터카 습격 — 거주자당 렌터카 체류 (제주 평균 = 1)
    rc = row.get("rentcar_index")
    if pd.notna(rc):
        if rc >= RENTCAR_HIGH:
            out["rentacar"] = {"value": f"{rc:.1f}배", "tone": "warn", "score": round(_rank(all_regions["rentcar_index"])[row["region_id"]] * 100),
                               "text": f"관광 렌터카가 제주 평균의 {rc:.1f}배 몰리는 동네예요. 주말 길이 붐벼요."}
        elif rc <= RENTCAR_LOW:
            out["rentacar"] = {"value": f"{rc:.1f}배", "tone": "good", "score": round(_rank(all_regions["rentcar_index"])[row["region_id"]] * 100),
                               "text": "관광 렌터카가 적은 생활 동네예요."}

    # 노포 / 오름 부자 / 요즘 뜨는 — 상위 25%만
    for key, col, fmt in (
        ("nopo", "nopo_ratio", lambda v: (f"{v:.0%}", f"20년 넘게 영업한 식당이 {v:.0%}예요. 삼춘 맛집이 많은 동네!")),
        ("oreum", "oreum_cnt", lambda v: (f"{int(v)}개", f"동네에 오름이 {int(v)}개 있어요.")),
        ("trend", "new_biz_rate", lambda v: (f"{v:.0%}", f"최근 3년 새로 연 가게 비율이 {v:.0%}로 높아요. 요즘 뜨는 동네예요.")),
    ):
        if col in all_regions.columns and pd.notna(row.get(col)):
            r = _rank(all_regions[col])[row["region_id"]]
            if r >= TOP_RANK:
                value, text = fmt(row[col])
                out[key] = {"value": value, "tone": "info", "score": round(r * 100), "text": text}

    # 귤 시즌 — 머무는 달에 출하가 몰리는 품종 (제주 전체 기준, 동네 구분 없음)
    g = _gyul()
    if g is not None:
        share = g[g["month"].isin(months)].groupby("variety")["share"].sum()
        peak = share[share >= GYUL_PEAK].sort_values(ascending=False)
        if not peak.empty:
            names = "·".join(peak.index[:3])
            out["gyul"] = {"value": names.split("·")[0], "tone": "good", "score": round(float(peak.iloc[0]) * 100),
                           "text": f"머무는 동안 {names} 제철이에요."}
    return out
