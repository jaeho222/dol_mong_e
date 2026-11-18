"""돌몽이의 한 달 살기 리허설 — 이 동네에서 평일 하루, 주말 하루를 보내면 어떨지.

장소 이름은 전부 데이터에서 가져온다 (지어내지 않음):
  카페·식당  906 구글 음식점 리뷰 × 780 (리뷰 20건↑ 평점순)        data/processed/region_places.csv
  오름        811 오름 위치 → 905 구글 관광지 리뷰 수로 유명한 순
  도서관      888 공공도서관 / 오일장 985 서귀포시 전통시장(개장일)
  캠핑장      810 / 해변 784 / 축제 761 / 날씨 877 (머무는 달의 빨래·바람)
일출·일몰은 동네 좌표(경도)로 정한다: 동쪽(126.8° 이상) 일출, 서쪽(126.5° 이하) 일몰.
"""
from datetime import date, timedelta
from functools import lru_cache

import pandas as pd

from backend import config
from backend.schema import Conditions
from backend.tools.data_loader import get_region

PLACES = config.ROOT_DIR / "data" / "processed" / "region_places.csv"
FEST = config.ROOT_DIR / "data" / "processed" / "festival.csv"
WEATHER = config.ROOT_DIR / "data" / "processed" / "weather_month.csv"


@lru_cache
def _places() -> pd.DataFrame:
    return pd.read_csv(PLACES) if PLACES.exists() else pd.DataFrame(columns=["region_id", "kind", "name", "rating", "reviews", "extra"])


def _pick(rid, kind, i=0):
    df = _places()
    rows = df[(df.region_id == rid) & (df.kind == kind)]
    if rows.empty:
        return None
    return rows.iloc[min(i, len(rows) - 1)].to_dict()


def _all(rid, kind):
    df = _places()
    return df[(df.region_id == rid) & (df.kind == kind)].to_dict("records")


def _rated(p):
    return f" (구글 평점 {p['rating']:.1f}, 리뷰 {int(p['reviews'])}건)" if p and pd.notna(p.get("rating")) else ""


def _market_on(m, d: date) -> bool:
    ex = str(m.get("extra") or "")
    return ex == "매일" or str(d.day % 10) in ex.split(",")


def _next_weekend(start: date) -> date:
    return start + timedelta(days=(5 - start.weekday()) % 7)


def rehearse(region_id: str, conditions: dict | Conditions) -> dict:
    cond = conditions if isinstance(conditions, Conditions) else Conditions.from_dict(conditions)
    row = get_region(region_id)
    rid, name = region_id, row["name"]
    start = cond.resolved_start()
    month = start.month
    lon = float(row["lon"])
    side = "sunrise" if lon >= 126.8 else "sunset" if lon <= 126.5 else "sea"
    beaches = [b.strip() for b in str(row.get("beaches") or "").split(",") if b.strip() and str(row.get("beaches")) != "nan"]
    beach = beaches[0] + " 해변" if beaches else None
    cafe, cafe2 = _pick(rid, "cafe"), _pick(rid, "cafe", 1)
    food, food2, food3 = _pick(rid, "food"), _pick(rid, "food", 1), _pick(rid, "food", 2)
    lib = _pick(rid, "library")
    oreum, oreum2 = _pick(rid, "oreum"), _pick(rid, "oreum", 1)
    camp = _pick(rid, "camping")
    markets = _all(rid, "market")
    car = cond.car is not False
    move = "차로" if car else "버스로"
    sources = set()

    # 날씨: 머무는 첫 달
    w = pd.read_csv(WEATHER) if WEATHER.exists() else pd.DataFrame()
    wm = w[(w.station == row["weather_station"]) & (w.month == month)] if not w.empty else w
    laundry = float(wm.laundry_share.iloc[0]) if len(wm) else None
    windy = float(wm.windy_share.iloc[0]) if len(wm) else None

    wd = []  # 평일
    if side == "sunrise":
        wd.append(("06:50", "일출 보며 하루 시작", beach or (oreum or {}).get("name") or "동쪽 바닷가",
                   "동쪽 해안 동네라 해 뜨는 쪽이 바다예요 (동네 좌표 기준)"))
    elif beach:
        wd.append(("07:30", "바닷가 아침 산책", beach, "784 해수욕장 정보"))
        sources.add("784 해수욕장 정보")
    elif oreum:
        wd.append(("07:30", "오름 아침 산책", oreum["name"], "811 오름 위치"))
    if cond.remote_work:
        if cafe:
            wd.append(("09:30", "카페에서 오전 업무", cafe["name"], "평점 높은 카페" + _rated(cafe)))
        elif lib:
            wd.append(("09:30", "도서관에서 오전 업무", lib["name"], "888 공공도서관 (동네에 평점 높은 카페 데이터가 없어요)"))
        else:
            wd.append(("09:30", "숙소에서 오전 업무", "숙소", f"공공와이파이 {int(row.get('wifi_ap') or 0)}곳"))
    else:
        wd.append(("10:00", "동네 한 바퀴", f"{name} 골목", f"상가 {int(row['amenity_cnt'])}곳이 있는 동네"))
    if food:
        wd.append(("12:30", "점심", food["name"], "동네 식당 평점 1위" + _rated(food)))
    if cond.remote_work:
        wd.append(("14:00", "오후 업무", lib["name"] if lib else (cafe2 or cafe or {}).get("name", "숙소"),
                   "888 공공도서관" if lib else "조용한 카페"))
    elif cond.with_kids:
        wd.append(("14:00", "아이와 도서관", lib["name"] if lib else "동네 산책",
                   f"소아 진료 가능 병·의원 {int(row['pediatric_cnt'])}곳"))
    else:
        wd.append(("14:00", "카페에서 쉬기", (cafe or {}).get("name", "동네 카페"), _rated(cafe).strip(" ()") or "동네 카페"))
    daily_mkt = next((m for m in markets if m.get("extra") == "매일"), None)
    if side == "sunset":
        wd.append(("17:30", "일몰 보기", beach or (oreum or {}).get("name") or "서쪽 바닷가",
                   "서쪽 해안 동네라 해 지는 쪽이 바다예요 (동네 좌표 기준)"))
    elif daily_mkt:
        wd.append(("17:30", "시장에서 장보기", daily_mkt["name"], "985 서귀포시 전통시장 (매일 열림)"))
    else:
        wd.append(("17:30", "마트 장보기", "동네 마트·편의점", f"슈퍼·편의점·카페 등 {int(row['amenity_cnt'])}곳"))
    wd.append(("19:00", "집밥", "숙소", "식비는 취사 위주로 계산했어요 (1인 월 60만 원)"))
    if laundry is not None:
        wd.append(("21:00", "빨래 널기", "숙소",
                   f"{month}월 {row['weather_station']} 관측소 기준, 습도 낮아 빨래 잘 마르는 날 {laundry:.0%} (877 일간 기후)"))

    we = []  # 주말
    sat = _next_weekend(start)
    if oreum:
        tip = f"구글 관광지 리뷰 {int(oreum['reviews'])}건" if pd.notna(oreum.get("reviews")) and oreum["reviews"] >= 20 else "811 오름 위치"
        we.append(("08:30", "오름 오르기", oreum["name"], tip + (f" · 바람 센 날 {windy:.0%}라 바람막이 챙기기" if windy and windy >= 0.4 else "")))
    mk = next((m for m in markets if m.get("extra") != "매일"), None)
    if mk:
        on = [d for d in (sat + timedelta(days=i) for i in range(0, 14)) if d.weekday() >= 5 and _market_on(mk, d)]
        when = f"{on[0].month}/{on[0].day}({'토일'[on[0].weekday() - 5]})" if on else "장날"
        we.append(("11:00", "오일장 구경", mk["name"], f"끝자리 {mk['extra']}일 장날 — 첫 주말 장날은 {when} (985 전통시장)"))
    if food2:
        we.append(("12:30", "점심", food2["name"], "동네 식당 평점 2위" + _rated(food2)))
    if cafe2 or cafe:
        c = cafe2 or cafe
        we.append(("14:30", "카페", c["name"], _rated(c).strip(" ()")))
    fest = pd.read_csv(FEST) if FEST.exists() else pd.DataFrame()
    end = start + timedelta(days=cond.days)
    fs = []
    for _, f in fest[fest.region_id == rid].iterrows() if not fest.empty else []:
        for y in (start.year, start.year + 1):
            try:
                fd = date(y, int(f.start_md[:2]), int(f.start_md[3:]))
            except ValueError:
                continue
            if start <= fd <= end:
                fs.append((fd, f["name"]))
    if fs:
        fd, fn = sorted(fs)[0]
        we.append(("16:00", "동네 축제", fn, f"{fd.month}/{fd.day} 시작 (761 VISIT JEJU 축제행사)"))
    elif camp and month in (4, 5, 6, 9, 10):
        we.append(("16:00", "캠핑장 피크닉", camp["name"], "810 캠핑 장소"))
    elif oreum2:
        we.append(("16:00", "오름 하나 더", oreum2["name"], "811 오름 위치"))
    if side == "sunset":
        we.append(("18:00", "노을 보며 저녁", food3["name"] if food3 else (beach or "서쪽 바닷가"),
                   ("동네 식당 평점 3위" + _rated(food3)) if food3 else "서쪽 바다"))
    elif food3:
        we.append(("18:00", "저녁 외식", food3["name"], "동네 식당 평점 3위" + _rated(food3)))

    notes = [f"이동은 {move}: " + (f"렌터카 기준" if car else f"정류장 {int(row['bus_stops'])}곳, 기·종점 노선 {int(row['bus_routes'])}개")]
    if cond.with_pet:
        notes.append(f"동물병원 {int(row.get('vet_cnt') or 0)}곳 (542 동물병원 현황)")
    if cond.with_kids:
        notes.append(f"응급실까지 약 {int(row['er_drive_min'])}분 (1046 응급실 보유 병원)")

    url = {n: u for n, u in zip(_places().name, _places().get("url", pd.Series(dtype=str))) if isinstance(u, str) and u}

    def fmt(items):
        # 카페·식당은 구글 지도 링크 (reviews.restaurant_monthly.google_maps_url). 관광지 등은 링크 없음
        return [{"time": t, "title": ti, "place": pl, "why": wy, "url": url.get(pl)} for t, ti, pl, wy in items]

    return {
        "region_id": rid, "region_name": name, "month": month,
        "weekday": fmt(wd), "weekend": fmt(we), "notes": notes,
        "sources": ["제주데이터허브 906·780 음식점, 811 오름, 905 관광지 리뷰, 888 도서관, 985 전통시장, 810 캠핑, 784 해수욕장, 761 축제, 877 기후"],
    }
