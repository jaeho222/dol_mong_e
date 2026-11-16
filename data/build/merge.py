"""data/interim/*.csv 를 region_id 기준으로 합쳐 data/processed/region_metrics.csv 를 만든다.

사용: python -m data.build.merge
아직 만들어지지 않은 지표는 sample 값으로 채우고 is_dummy=1 로 표시한다.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "sample" / "region_metrics.csv"
INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "data" / "processed" / "region_metrics.csv"


def main():
    base = pd.read_csv(SAMPLE).set_index("region_id")
    real_cols = set()
    for f in sorted(INTERIM.glob("*.csv")):
        part = pd.read_csv(f).set_index("region_id")
        cols = [c for c in part.columns if c in base.columns]
        base.update(part[cols])
        real_cols.update(cols)
        print(f"merged {f.name}: {cols}")

    metric_cols = [c for c in base.columns if c not in ("name", "city", "zone", "aliases", "lat", "lon", "is_dummy")]
    base["is_dummy"] = int(not set(metric_cols) <= real_cols)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    base.reset_index().to_csv(OUT, index=False)
    print(f"→ {OUT} (still dummy: {sorted(set(metric_cols) - real_cols)})")


if __name__ == "__main__":
    main()
