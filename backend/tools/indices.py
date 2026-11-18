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
NOISE_WECPNL = 75        # 항공기 소음: 공항소음방지법 소음대책지역 기준(WECPNL 75)
BRIX_DIFF = 0.4          # 귤 당도: 제주 평균보다 0.4 Brix 이상 달 때 (측정 농가 8곳 이상)
BRIX_MIN_SAMPLES = 8
GYUL_MONTHS = {10, 11, 12, 1, 2, 3}
RAINY_MONTHS = {6, 7, 8, 9}
SNOW_MONTHS = {12, 1, 2}
FOOD_TOP_MIN = 5         # 맛집: 구글 평점 4.5 이상(리뷰 20건↑) 식당이 5곳 이상
FESTIVAL_MAX = 3         # 축제: 머무는 동안 열리는 것 최대 3개까지 이름 표시


@lru_cache(maxsize=1)
def _weather() -> pd.DataFrame | None:
    p = PROCESSED / "weather_month.csv"
    return pd.read_csv(p) if p.exists() else None


@lru_cache(maxsize=1)
def _festival() -> pd.DataFrame | None:
    p = PROCESSED / "festival.csv"
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


def _festivals_in_stay(region_id: str, cond: Conditions) -> list[str]:
    """축제 날짜(월-일)를 머무는 해에 다시 놓고 체류 기간과 겹치는지 본다. 연말에 걸친 축제도 처리."""
    f = _festival()
    if f is None:
        return []
    start = cond.resolved_start()
    end = start + timedelta(days=max(cond.days, 1) - 1)
    names = []
    for _, r in f[f["region_id"] == region_id].iterrows():
        for year in range(start.year - 1, end.year + 1):
            try:
                s = start.replace(year=year, month=int(r.start_md[:2]), day=int(r.start_md[3:]))
                e = start.replace(year=year, month=int(r.end_md[:2]), day=int(r.end_md[3:]))
            except ValueError:  # 2월 29일
                continue
            if e < s:
                e = e.replace(year=year + 1)
            if s <= end and e >= start:
                names.append(r["name"])
                break
    return names


def _rank(s: pd.Series) -> pd.Series:
    return (s.rank(method="average") - 1) / max(len(s) - 1, 1)


SOURCES = {
    "laundry": "제주데이터허브 877 일간 기후(2000~2021) — 습도 65% 미만인 날 비율, 가까운 관측소 기준",
    "hair": "제주데이터허브 877 일간 기후(2000~2021) — 일 최대풍속 10m/s 이상인 날 비율",
    "rentacar": "제주데이터허브 1208 렌터카 체류 위치(2021 하반기) ÷ 583 거주 인구(2025-10)",
    "nopo": "제주데이터허브 780 음식점 목록 — 영업 중 식당 중 2006년 이전 인허가 비율",
    "oreum": "제주데이터허브 811 오름 위치 — 지번주소 기준",
    "trend": "제주데이터허브 830 읍면동 사업체 생멸 — 2021~2023 신생 ÷ 활동 사업체",
    "gyul": "제주데이터허브 855 신고소별 감귤 출하량(2018~2025-03) — 품종별 월 출하 비중",
    "gyul_sweet": "제주데이터허브 857 고품질 감귤 당도(2020-11~12)",
    "noise": "제주데이터허브 783 공항 인근 항공기 소음도(2022, WECPNL)",
    "pet": "공공데이터포털(허브 542) 제주 동물병원 현황",
    "flood": "공공데이터포털(허브 435) 제주시 자연재해위험개선지구 — 정비 미완료 침수위험지구",
    "snow": "공공데이터포털(허브 131) 제설 모래주머니 적치 노선 — 지나가는 권역은 수동 매핑",
    "food": "제주데이터허브 906 구글 음식점 리뷰 × 780 음식점 목록(상호 매칭)",
    "festival": "제주데이터허브 761 VISIT JEJU 축제행사 — 이름에 동네 이름이 든 축제만",
}


def region_indices(row: dict, all_regions: pd.DataFrame, cond: Conditions) -> dict:
    out = _region_indices(row, all_regions, cond)
    for k, v in out.items():
        v["source"] = SOURCES.get(k, "")
    return out


def _region_indices(row: dict, all_regions: pd.DataFrame, cond: Conditions) -> dict:
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

    # ✈️ 항공기 소음 — 2022년 WECPNL, 공항 소음대책지역 기준(75) 이상인 측정소가 있는 권역
    nz = row.get("noise_wecpnl")
    if pd.notna(nz) and nz >= NOISE_WECPNL:
        out["noise"] = {"value": f"{nz:.0f}", "tone": "warn", "score": round(min(nz, 100)),
                        "text": f"공항 가까운 {row.get('noise_stations')} 측정소에서 소음도(WECPNL)가 높아요. 75 이상이면 소음대책지역 기준이에요."}

    # 🍊 귤 당도 — 귤철에만, 측정 농가가 충분하고 제주 평균보다 확실히 달 때
    gb, gn = row.get("gyul_brix"), row.get("gyul_samples")
    if set(months) & GYUL_MONTHS and pd.notna(gb) and pd.notna(gn) and gn >= BRIX_MIN_SAMPLES and "gyul_brix" in all_regions:
        valid = all_regions.dropna(subset=["gyul_brix", "gyul_samples"])
        avg = (valid["gyul_brix"] * valid["gyul_samples"]).sum() / valid["gyul_samples"].sum()
        if gb - avg >= BRIX_DIFF:
            out["gyul_sweet"] = {"value": f"{gb:.1f}Brix", "tone": "good", "score": round(gb * 5),
                                 "text": f"이 동네 귤 당도 평균 {gb:.1f}Brix로 제주 평균({avg:.1f})보다 달아요. (2020년 측정 {int(gn)}농가)"}

    # 🐶 댕댕이 — 반려동물과 갈 때만
    vc = row.get("vet_cnt")
    if cond.with_pet and pd.notna(vc) and "vet_cnt" in all_regions:
        r = _rank(all_regions["vet_cnt"].fillna(0))[row["region_id"]]
        if r >= TOP_RANK:
            out["pet"] = {"value": f"{int(vc)}곳", "tone": "good", "score": round(r * 100), "text": f"동물병원이 {int(vc)}곳 있어요."}
        elif vc <= 1:
            out["pet"] = {"value": f"{int(vc)}곳", "tone": "warn", "score": round(r * 100), "text": "동물병원이 1곳 이하예요. 가까운 시내 병원을 미리 알아두세요."}

    # 🌧 침수 — 장마·태풍철에 정비가 덜 끝난 침수위험지구가 있으면 (제주시 자료만 있음)
    fz = row.get("flood_zones")
    if set(months) & RAINY_MONTHS and pd.notna(fz) and fz >= 1:
        out["flood"] = {"value": f"{int(fz)}곳", "tone": "warn", "score": min(int(fz) * 25, 100),
                        "text": f"비 많이 오는 철엔 {row.get('flood_names')} 쪽 침수위험지구를 피하세요."}

    # ❄️ 폭설 — 겨울에 산간 통제 도로가 지나가는 권역
    sr = row.get("snow_roads")
    if set(months) & SNOW_MONTHS and isinstance(sr, str) and sr:
        out["snow"] = {"value": sr.split(", ")[0], "tone": "warn", "score": 50,
                       "text": f"눈 오면 {sr}가 자주 통제돼요. 한라산 넘어가는 길은 미리 확인하세요."}

    # ⭐ 맛집 — 구글 평점 4.5 이상 식당이 많은 동네
    ft = row.get("food_top")
    if pd.notna(ft) and ft >= FOOD_TOP_MIN:
        out["food"] = {"value": f"{int(ft)}곳", "tone": "info", "score": round(_rank(all_regions["food_top"].fillna(0))[row["region_id"]] * 100),
                       "text": f"구글 평점 4.5 이상(리뷰 20건↑) 식당이 {int(ft)}곳이에요. (2020~2021 리뷰)"}

    # 🎉 축제 — 머무는 동안 이 동네에서 열리는 축제 (이름에 동네 이름이 든 것만)
    fest = _festivals_in_stay(row["region_id"], cond)
    if fest:
        out["festival"] = {"value": f"{len(fest)}개", "tone": "good", "score": min(len(fest) * 20, 100),
                           "text": "머무는 동안 " + ", ".join(fest[:FESTIVAL_MAX])
                           + (f" 등 {len(fest)}개 축제가 열려요." if len(fest) > FESTIVAL_MAX else " 축제가 열려요.")}

    # 귤 시즌 — 머무는 달에 출하가 몰리는 품종. 출하 통계(855)는 제주 전체라서,
    #   귤 농가가 있는 동네(당도 측정 농가 3곳 이상, 857)에만 띄운다 → 시내권엔 안 뜸
    g = _gyul()
    if g is not None and pd.notna(gn) and gn >= 3:
        share = g[g["month"].isin(months)].groupby("variety")["share"].sum()
        peak = share[share >= GYUL_PEAK].sort_values(ascending=False)
        if not peak.empty:
            names = "·".join(peak.index[:3])
            out["gyul"] = {"value": names.split("·")[0], "tone": "good", "score": round(float(peak.iloc[0]) * 100),
                           "text": f"머무는 동안 {names} 제철이에요."}
    return out
