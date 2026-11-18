-- =====================================================================
-- 25_season_indices.sql — 머무는 달에 따라 달라지는 지수 재료
-- refined.weather_month : 관측소 × 월 — 빨래 잘 마르는 날·강풍 부는 날 비율 (877, 2000~2021)
-- refined.gyul_month    : 품종 × 월 — 연간 출하량 중 그 달 비중 (855, 2018~2025-03)
-- 앱은 data/processed/weather_month.csv, gyul_month.csv 로 읽는다 (export_supabase.py)
-- =====================================================================

create or replace function refined.num(t text) returns numeric language sql immutable as $$
  select case when trim(t) ~ '^-?[0-9.]+$' then trim(t)::numeric end $$;

-- 877 원본 문제: 제주 관측소 파일의 Sunshine_mean 은 평균 0.38시간/일로 깨져 있다(다른 관측소 5.5 안팎).
--   Solar_mean(5.86)은 일사량(MJ/㎡)이라 대신 쓸 수 없다(1월 182시간이 돼 평년값 70시간과 안 맞음) → 제주 일조는 null
create or replace view refined.weather_daily as
select "관측소" station, "Date"::date d, extract(month from "Date"::date)::int m,
       refined.num("Tem_mean") temp, refined.num("Humid_mean") humid,
       refined.num("Wspeed_mean") wind_mean, refined.num("Wspeed_max") wind_max,
       case when "관측소" = '제주' then null else refined.num("Sunshine_mean") end sunshine
from raw.hub_877 where "Date" ~ '^\d{4}-\d{2}-\d{2}$';

-- 빨래 좋은 날: 평균습도 65% 미만인 날.
--   일조가 멀쩡한 3개 관측소에서 '습도 70% 미만 + 일조 5시간 이상' 비율과 월별 r=0.91 → 일조가 깨진 제주까지 같은 기준으로 비교 가능
-- 산발 날: 일 최대풍속 10m/s 이상
create or replace view refined.weather_month as
select station, m as month, count(*) days,
       round(avg((humid < 65)::int), 3) laundry_share,
       round(avg((wind_max >= 10)::int), 3) windy_share,
       round(avg(humid), 1) humid_avg, round(avg(wind_max), 1) wind_max_avg, round(avg(sunshine), 1) sunshine_avg
from refined.weather_daily where humid is not null and wind_max is not null
group by 1, 2;

create or replace view refined.gyul_month as
with t as (select "품종소분류" variety, extract(month from "출하일자"::date)::int m, sum(refined.num("출하량")) qty
           from raw.hub_855 where "출하일자" ~ '^\d{4}-\d{2}-\d{2}$' group by 1, 2)
select variety, m as month, round(qty / sum(qty) over (partition by variety), 3) share,
       round(sum(qty) over (partition by variety)) total_qty
from t;

-- 1월 기온·일조 (제주 일조는 깨져 있어 기상청 평년값 기반 70시간, jeju.com 겨울 팁)
create or replace view refined.m_weather as
with st(name, lat, lon) as (values ('제주',33.514,126.530),('고산',33.294,126.163),('성산',33.387,126.880),('서귀포',33.246,126.565)),
jan as (select station st, avg(temp) t, coalesce(avg(sunshine) * 31, 70) sun from refined.weather_daily where m = 1 group by 1),
near as (select distinct on (r.region_id) r.region_id, st.name from refined.regions r cross join st
         order by r.region_id, (r.lat - st.lat)^2 + (r.lon - st.lon)^2)
select near.region_id, near.name weather_station, round(jan.t, 1) jan_temp, round(jan.sun) sunshine_jan
from near join jan on jan.st = near.name;
