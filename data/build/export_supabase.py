"""Supabase(refined.region_metrics, refined.care_points_mat)에서 앱용 CSV를 내보낸다.

사용: python -m data.build.export_supabase
필요: .env 의 SUPABASE_DB_URL (Supabase 대시보드 → Connect → Session pooler 연결 문자열), `pip install psycopg[binary]`

앱(backend)은 Supabase에 직접 붙지 않고 이 스크립트가 만든 CSV만 읽는다.
→ 제주빅데이터센터 PC에서도 DB 접속 없이 실행 가능.
"""
import csv
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "processed"

QUERIES = {
    "region_metrics.csv": """
        select * from refined.region_metrics
        order by array_position(array['jeju_new','jeju_old','aewol','hallim','hangyeong','jocheon','gujwa',
                                      'seongsan','pyoseon','namwon','seogwipo_dong','jungmun','andeok','daejeong'], region_id)""",
    "care_points.csv": "select id, kind, name, lat, lon, region_id, detail, source_id, base_date from refined.care_points_mat order by id",
    "weather_month.csv": "select station, month, days, laundry_share, windy_share, humid_avg, wind_max_avg from refined.weather_month order by station, month",
    "gyul_month.csv": "select variety, month, share, total_qty from refined.gyul_month order by variety, month",
}


def main():
    load_dotenv(ROOT / ".env")
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise SystemExit("SUPABASE_DB_URL 이 .env 에 없습니다")
    import psycopg

    OUT.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(url) as conn:
        for name, sql in QUERIES.items():
            with conn.cursor() as cur:
                cur.execute(sql)
                cols = [d.name for d in cur.description]
                rows = cur.fetchall()
            with open(OUT / name, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(cols)
                w.writerows(rows)
            print(f"→ {OUT / name} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
