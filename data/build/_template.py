"""새 지표 수집 스크립트 템플릿 — 복사해서 이름만 바꿔 쓰세요.

규칙
- 입력: data/raw/ (커밋 금지) 또는 API (키는 .env)
- 출력: data/interim/<이름>.csv — 반드시 region_id 컬럼 + region_metrics 컬럼명과 같은 이름
- 실행: python -m data.build.<이름>
"""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
OUT = ROOT / "data" / "interim" / "TEMPLATE.csv"

# 읍면동 이름 → region_id 매핑은 sample CSV의 name/aliases 를 재사용
REGIONS = pd.read_csv(ROOT / "data" / "sample" / "region_metrics.csv")


def to_region_id(emd_name: str) -> str | None:
    for _, r in REGIONS.iterrows():
        if r["name"] in emd_name or any(a and a in emd_name for a in str(r["aliases"]).split("|")):
            return r["region_id"]
    return None


def main():
    key = os.getenv("DATA_GO_KR_KEY")  # noqa: F841  필요할 때 사용
    # 1) 원본 읽기 / API 호출
    # 2) 읍면동 → region_id 매핑 (to_region_id)
    # 3) region_id 별 집계
    df = pd.DataFrame(columns=["region_id"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)


if __name__ == "__main__":
    main()
