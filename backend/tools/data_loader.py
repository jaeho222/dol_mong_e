"""읍면동 지표 테이블 로더.

Agent와 계산 도구는 모두 이 테이블 하나만 본다.
실제 데이터 수집·전처리는 data/build/ 의 스크립트가 담당하고, 결과를
config.REGION_METRICS_PATH 위치의 CSV로 저장하면 된다. (스키마는 docs/DATA.md)
"""
from functools import lru_cache

import pandas as pd

from backend import config

REQUIRED_COLUMNS = [
    "region_id", "name", "city", "zone", "aliases", "lat", "lon",
    "base_stay_month", "rent_index",
    "bus_stops", "bus_routes", "amenity_cnt",
    "hospital_cnt", "pediatric_cnt", "er_drive_min",
    "jan_temp", "sunshine_jan", "crowd_index",
    "wifi_ap", "cowork_cnt",
    "inland_heating_risk", "odor_flag", "snow_road_flag",
    "is_dummy",
]


@lru_cache(maxsize=1)
def load_regions() -> pd.DataFrame:
    df = pd.read_csv(config.REGION_METRICS_PATH)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"region_metrics.csv에 컬럼이 없습니다: {missing}")
    df["aliases"] = df["aliases"].fillna("")
    return df.set_index("region_id", drop=False)


def get_region(region_id: str) -> dict:
    df = load_regions()
    if region_id not in df.index:
        raise KeyError(f"알 수 없는 지역: {region_id}")
    return df.loc[region_id].to_dict()


def find_region_ids(text: str) -> list[str]:
    """자유 텍스트에서 지역명/별칭을 찾아 region_id 목록으로 반환."""
    found = []
    for rid, row in load_regions().iterrows():
        names = [row["name"]] + [a for a in str(row["aliases"]).split("|") if a]
        if any(n and n in text for n in names):
            found.append(rid)
    return found


def data_is_dummy() -> bool:
    return bool(load_regions()["is_dummy"].astype(int).any())
