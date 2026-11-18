-- =====================================================================
-- 26_more_indices.sql — 동네 지수 추가 재료 (항공기 소음, 귤 당도, 댕댕이, 침수, 폭설 도로, 맛집 평점, 축제)
-- 화면 표시 여부(임계값)는 backend/tools/indices.py 가 정한다.
-- =====================================================================

-- ✈️ 항공기 소음(783): 제주공항 측정소의 2022년(WECPNL 마지막 완전 연도) 분기 평균, 권역별 최댓값
--   2023년 값은 단위가 Lden 으로 바뀌어(값이 10 이상 낮게 나옴) 쓰지 않는다. WECPNL 75 이상 = 소음대책지역 기준
create or replace view refined.m_noise as
with st as (
  select "소음측정소" station, refined.region_of('제주시 ' || "소음측정소") region_id,
         avg(refined.num("소음도(단위:WECPNL)")) wecpnl
  from raw.hub_783 where "공항" like '제주%' and "연도" like '2022%'
  group by 1, 2)
select region_id, round(max(wecpnl), 1) noise_wecpnl,
       string_agg(station || ' ' || round(wecpnl), ', ' order by wecpnl desc) noise_stations
from st where region_id is not null and wecpnl is not null group by 1;

-- 🍊 귤 당도(857): 2020-11~12 고품질 감귤 당도 측정 농가, 권역 평균(Brix)
create or replace view refined.m_gyul_brix as
select refined.region_of("시군구" || ' ' || "읍면동") region_id, round(avg(refined.num("당도")), 2) gyul_brix, count(*) gyul_samples
from raw.hub_857 group by 1;

-- 🐶 댕댕이(542): 동물병원 수, 이름에 24 들어간 곳
create or replace view refined.m_pet as
select refined.region_of("소재지") region_id, count(*) vet_cnt, count(*) filter (where "업체명" ~ '24') vet_24h
from raw.hub_542 group by 1;

-- 🌧 침수(435, 제주시만): 침수위험 지구 중 아직 정비가 끝나지 않은 곳(추진 중·보류)
create or replace view refined.m_flood as
select refined.region_of('제주시 ' || "위치") region_id, count(*) flood_zones, string_agg("지구명", ', ') flood_names
from raw.hub_435
where "유형" = '침수위험' and coalesce("완료여부", '') not like '%완료%'
group by 1;

-- ❄️ 폭설 통제 도로(131): 모래주머니를 쌓아두는 산간 도로 중 겨울 통제가 잦은 3개 노선 → 지나가는 권역 (수동 매핑)
create table if not exists refined.snow_road_region (road text, region_id text);
truncate refined.snow_road_region;
insert into refined.snow_road_region values
 ('5·16도로', 'jeju_old'), ('5·16도로', 'seogwipo_dong'),
 ('1100도로', 'jeju_new'), ('1100도로', 'jungmun'),
 ('번영로', 'jeju_old'), ('번영로', 'jocheon'), ('번영로', 'pyoseon');
create or replace view refined.m_snow as
select region_id, string_agg(road, ', ' order by road) snow_roads from refined.snow_road_region group by 1;

-- ⭐ 맛집 평점: 구글 음식점 월간 평점(906)을 음식점 목록(780)의 상호명으로 동네에 붙인다.
--   상호가 제주 안에서 하나뿐인 영업 중 가게만 매칭(체인점·동명 가게 제외), 리뷰 20건 이상인 가게만
create or replace view refined.food_place as
with uniq as (
  select "사업장명" name, min("소재지전체주소") addr from raw.hub_780
  where "영업상태명" like '영업%' group by 1 having count(*) = 1),
rv as (
  select place_name name, sum(refined.num(avg_rating) * refined.num(review_count)) / nullif(sum(refined.num(review_count)), 0) rating,
         sum(refined.num(review_count)) reviews
  from reviews.restaurant_monthly group by 1)
select rv.name, refined.region_of(u.addr) region_id, round(rv.rating, 2) rating, rv.reviews
from rv join uniq u using (name) where rv.reviews >= 20;

create or replace view refined.m_food as
select region_id, count(*) food_places, round(avg(rating), 2) food_rating,
       count(*) filter (where rating >= 4.5) food_top
from refined.food_place where region_id is not null group by 1;

-- 🎉 축제(761): 위치 컬럼이 없어 축제 이름에 동네 이름(권역 키워드·별칭)이 들어 있을 때만 권역에 붙인다
create or replace view refined.festival as
with f as (
  select distinct on (regexp_replace("콘텐츠명", '^(제?\d+회|\d{4}년?)\s*', ''))
         regexp_replace("콘텐츠명", '^(제?\d+회|\d{4}년?)\s*', '') name, "시작일"::date s, "종료일"::date e
  from raw.hub_761 where "시작일" ~ '^\d{4}-\d{2}-\d{2}$' and "종료일" ~ '^\d{4}-\d{2}-\d{2}$'
  order by regexp_replace("콘텐츠명", '^(제?\d+회|\d{4}년?)\s*', ''), "시작일" desc),
kw as (
  select region_id, keyword from refined.region_keyword where length(keyword) >= 2
  union select region_id, unnest(string_to_array(aliases, '|')) from refined.regions)
select f.name, to_char(f.s, 'MM-DD') start_md, to_char(f.e, 'MM-DD') end_md, (f.e - f.s) days,
       (select kw.region_id from kw where f.name like '%' || kw.keyword || '%' order by length(kw.keyword) desc limit 1) region_id
from f where (f.e - f.s) <= 120 and f.name not like '%취소%';   -- 반년짜리 전시·상설 행사, 취소된 행사 제외

-- 최종 앱용 view: 20_region_metrics.sql 의 정의에 위 지표들을 붙여 다시 만든다
drop view if exists refined.region_metrics;
create view refined.region_metrics as
select r.region_id, r.name, r.city, r.zone, r.aliases, r.lat, r.lon,
  m.base_stay_month, coalesce(rent.rent_index, 1.0) rent_index,
  coalesce(bus.bus_stops, 0) bus_stops, coalesce(bus.bus_routes, 0) bus_routes,
  coalesce(am.amenity_cnt, 0) amenity_cnt,
  coalesce(med.hospital_cnt, 0) hospital_cnt, coalesce(med.pediatric_cnt, 0) pediatric_cnt,
  er.er_drive_min, w.jan_temp, w.sunshine_jan, cr.crowd_index,
  m.wifi_ap, m.cowork_cnt, m.inland_heating_risk, od.odor_flag, m.snow_road_flag,
  0 is_dummy,
  ex.rentcar_stays, ex.rentcar_index, ex.oreum_cnt, ex.nopo_ratio, ex.restaurant_cnt, ex.new_biz_rate,
  od.pig_farms, rent.rent_samples, w.weather_station,
  nz.noise_wecpnl, nz.noise_stations, gb.gyul_brix, gb.gyul_samples, pt.vet_cnt,
  coalesce(fl.flood_zones, 0) flood_zones, fl.flood_names, sn.snow_roads,
  fd.food_places, fd.food_rating, fd.food_top
from refined.regions r
join refined.region_metrics_manual m using (region_id)
left join refined.m_rent rent using (region_id)
left join refined.m_bus bus using (region_id)
left join refined.m_amenity am using (region_id)
left join refined.m_medical med using (region_id)
left join refined.m_er er using (region_id)
left join refined.m_weather w using (region_id)
left join refined.m_crowd cr using (region_id)
left join refined.m_odor od using (region_id)
left join refined.m_extra ex using (region_id)
left join refined.m_noise nz using (region_id)
left join refined.m_gyul_brix gb using (region_id)
left join refined.m_pet pt using (region_id)
left join refined.m_flood fl using (region_id)
left join refined.m_snow sn using (region_id)
left join refined.m_food fd using (region_id);
-- festival.csv 는 refined.festival 중 region_id 가 있는 것에서 중복(이름 표기만 다른 같은 축제)과
-- 축제가 아닌 공연·전시·판촉 행사 7건을 손으로 뺐다.
