-- =====================================================================
-- 30_care_points.sql
-- '세심 체크' 배지·재미 지수용 지점 레이어. 위경도가 있는 데이터만 모은다.
-- 결과: refined.care_points (view) — kind, name, lat, lon, region_id, detail, source_id, base_date
-- 예) 숙소 반경 300m 클린하우스:  where kind='clean_house' and st_dwithin(...)
-- 1352 환경소음은 TM 좌표가 표준 좌표계로 변환되지 않아(원점 불명) 제외, 권역 단위로만 사용.
-- =====================================================================
create or replace view refined.care_points as
with p as (
  select 'cctv_safety' kind, "관리기관명" || ' ' || coalesce("도로명주소", "지번주소") name,
         "위도"::float lat, "경도"::float lon, "설치목적" || ' · 카메라 ' || "카메라대수" || '대' detail, 846 source_id, "데이터기준일" base_date
  from raw.hub_846 where "위도" ~ '^[0-9.]+$' and "설치목적" ~ '(방범|생활|어린이)'
  union all
  select 'clean_house', coalesce("단지_명", "도로명_주소"), "위도_좌표"::float, "경도_좌표"::float,
         '음식물 ' || coalesce("음식물_수거함_수", '0') || ' · 재활용 ' || coalesce("재활용_수거함_수", '0') || ' · CCTV ' || coalesce("CCTV_설치_수", '0'), 1335, "등록_일시"
  from raw.hub_1335 where "위도_좌표" ~ '^[0-9.]+$'
  union all
  select 'accident_hotspot', "occurrencePlace", "latitude"::float, "longitude"::float,
         '사고 ' || "occurrenceCount" || '건 · 사상자 ' || "deathInjuryCount" || '명', 863, '2017~2023'
  from raw.hub_863 where "latitude" ~ '^[0-9.]+$'
  union all
  select 'oreum', "placeName", "latitude"::float, "longitude"::float, "category", 811, '2025-09'
  from raw.hub_811 where "latitude" ~ '^[0-9.]+$'
  union all
  select 'museum', "placeName", "latitude"::float, "longitude"::float, "category", 812, '2025-09'
  from raw.hub_812 where "latitude" ~ '^[0-9.]+$'
  union all
  select 'camping', "placeName", "latitude"::float, "longitude"::float, "category", 810, '2025-09'
  from raw.hub_810 where "latitude" ~ '^[0-9.]+$'
  union all
  select 'pharmacy_store', "상호명", "위도"::float, "경도"::float, "상권업종소분류명", 793, '2025-09'
  from raw.hub_793 where "상권업종소분류명" in ('약국', '편의점') and "위도" ~ '^[0-9.]+$'
)
select row_number() over () id, kind, name, lat, lon, refined.region_of_point(lon, lat) region_id, detail, source_id, base_date
from p where lat between 33.0 and 33.6 and lon between 126.1 and 127.0;

comment on view refined.care_points is '세심 포인트 지점(위경도). kind: cctv_safety, clean_house, accident_hotspot, oreum, museum, camping, pharmacy_store';

-- 조회가 잦으면 머티리얼라이즈해서 쓴다 (region_of_point 계산이 지점마다 돌아서)
create table if not exists refined.care_points_mat as select * from refined.care_points with no data;
truncate refined.care_points_mat;
insert into refined.care_points_mat select * from refined.care_points;
create index if not exists care_points_mat_kind on refined.care_points_mat (kind, region_id);
