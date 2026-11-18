-- =====================================================================
-- 27_priority_factors.sql — 사용자가 고르는 '중요한 것 3가지' 중 새로 필요한 재료
--   밤길 안심(CCTV + 112 신고), 자연(오름 + 캠핑장 + 해변)
-- =====================================================================

-- 🔦 CCTV(846): 설치목적이 관리기관마다 달라(제주시는 대부분 교통단속, 방범·어린이보호는 서귀포시 자료에만 있음)
--   목적으로 거르면 지역 편향이 생긴다 → 목적 구분 없이 공공 CCTV 카메라 대수를 거주 인구(583)로 나눈다.
-- 🚓 112 신고(491, 2025): 경찰서 3곳(동부·서부·서귀포) 단위뿐 → 관할 권역에 같은 값. 주민+방문객 1인당, 제주 평균=1
--   관할은 대략적 매핑: 동부서=원도심·조천·구좌, 서부서=신도심·애월·한림·한경, 서귀포서=서귀포시 전체
create or replace view refined.m_safety as
with pop as (select refined.region_of("city" || ' ' || "emd") region_id, sum("resdPop"::numeric) resd, sum("visitPop"::numeric) visit
             from raw.hub_583 group by 1),
cam as (select refined.region_of_point("경도"::float, "위도"::float) region_id, sum(coalesce(refined.num("카메라대수"), 1)) cams
        from raw.hub_846 where "위도" ~ '^[0-9.]+$' group by 1),
ps as (select region_id, case when region_id in ('jeju_old','jocheon','gujwa') then '동부서'
                               when region_id in ('jeju_new','aewol','hallim','hangyeong') then '서부서' else '서귀포서' end ps
       from refined.regions),
calls as (select '동부서' ps, refined.num("동부서") c from raw.hub_491 where "연도별" = '2025'
          union all select '서부서', refined.num("서부서") from raw.hub_491 where "연도별" = '2025'
          union all select '서귀포서', refined.num("서귀포서") from raw.hub_491 where "연도별" = '2025'),
ps_pop as (select ps.ps, sum(pop.resd + pop.visit) people from ps join pop using (region_id) group by 1)
select r.region_id, coalesce(cam.cams, 0) cctv_cams,
       round(coalesce(cam.cams, 0) / pop.resd / ((select sum(cams) from cam where region_id is not null) / (select sum(resd) from pop where region_id is not null)), 2) cctv_idx,
       ps.ps police_station,
       round((calls.c / ps_pop.people) / ((select sum(c) from calls) / (select sum(people) from ps_pop)), 2) police_call_idx
from refined.regions r join pop using (region_id) join ps using (region_id)
join calls on calls.ps = ps.ps join ps_pop on ps_pop.ps = ps.ps left join cam using (region_id);

-- 🌿 자연 재료: 캠핑장(810), 해변(784 — 이름에 지명만 있어 권역 키워드·별칭으로 매칭)
create or replace view refined.m_nature as
with kw as (select region_id, keyword from refined.region_keyword
            union select region_id, unnest(string_to_array(aliases, '|')) from refined.regions),
beach as (select distinct "해변명" name,
                 (select kw.region_id from kw where "해변명" like '%' || kw.keyword || '%' order by length(kw.keyword) desc limit 1) region_id
          from raw.hub_784)
select r.region_id,
       (select count(*) from refined.care_points_mat c where c.kind = 'camping' and c.region_id = r.region_id) camping_cnt,
       (select count(*) from beach b where b.region_id = r.region_id) beach_cnt,
       (select string_agg(b.name, ', ') from beach b where b.region_id = r.region_id) beaches
from refined.regions r;

-- 최종 앱용 view 에 위 재료를 붙인다 (26_more_indices.sql 의 정의 + safety·nature)
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
  fd.food_places, fd.food_rating, fd.food_top,
  sf.cctv_cams, sf.cctv_idx, sf.police_station, sf.police_call_idx,
  na.camping_cnt, na.beach_cnt, na.beaches
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
left join refined.m_food fd using (region_id)
left join refined.m_safety sf using (region_id)
left join refined.m_nature na using (region_id);
