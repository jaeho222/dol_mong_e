-- =====================================================================
-- 20_region_metrics.sql
-- raw/refined 데이터로 앱이 읽는 region_metrics(14개 권역 × 지표)를 계산한다.
-- 결과: refined.region_metrics (view)  →  data/build/export_supabase.py 가 CSV로 저장
-- 컬럼 정의·한계는 docs/DATA.md
-- =====================================================================

-- 1) 권역 기본 정보 (앱 sample 과 동일한 14개, 대표 좌표 포함)
create table if not exists refined.regions (
  region_id text primary key, name text, city text, zone text, aliases text, lat double precision, lon double precision);
insert into refined.regions values
 ('jeju_new','제주시 신도심','제주시','제주시권','노형|연동|신제주',33.4868,126.4840),
 ('jeju_old','제주시 원도심','제주시','제주시권','삼도|일도|이도|원도심|제주시내',33.5110,126.5250),
 ('aewol','애월읍','제주시','서부','애월|곽지|한담',33.4630,126.3300),
 ('hallim','한림읍','제주시','서부','한림|협재|금능',33.4110,126.2650),
 ('hangyeong','한경면','제주시','서부','한경|고산|저지',33.3360,126.1900),
 ('jocheon','조천읍','제주시','동부','조천|함덕|선흘',33.5340,126.6350),
 ('gujwa','구좌읍','제주시','동부','구좌|월정|세화|김녕',33.5200,126.8520),
 ('seongsan','성산읍','서귀포시','동부','성산|섭지|온평',33.4350,126.9050),
 ('pyoseon','표선면','서귀포시','동부','표선|가시리',33.3270,126.8330),
 ('namwon','남원읍','서귀포시','서귀포권','남원|위미|신례',33.2800,126.7080),
 ('seogwipo_dong','서귀포 동지역','서귀포시','서귀포권','서귀포|서귀포시내|천지동|동홍',33.2530,126.5600),
 ('jungmun','중문·대천','서귀포시','서귀포권','중문|대천|강정',33.2520,126.4220),
 ('andeok','안덕면','서귀포시','남서부','안덕|사계|화순',33.2550,126.3200),
 ('daejeong','대정읍','서귀포시','남서부','대정|모슬포|영어교육도시',33.2250,126.2510)
on conflict (region_id) do nothing;

-- 2) 읍면동(행정·법정) 이름 → 권역 매핑 키워드. 읍면(prio 1)을 동(prio 2)보다 먼저 본다.
create table if not exists refined.region_keyword (region_id text, city text, keyword text, prio int);
truncate refined.region_keyword;
insert into refined.region_keyword
select r, c, k, p from (values
 ('aewol','제주시','애월',1),('hallim','제주시','한림',1),('hangyeong','제주시','한경',1),
 ('jocheon','제주시','조천',1),('gujwa','제주시','구좌',1),('gujwa','제주시','우도',1),
 ('seongsan','서귀포시','성산',1),('pyoseon','서귀포시','표선',1),('namwon','서귀포시','남원',1),
 ('andeok','서귀포시','안덕',1),('daejeong','서귀포시','대정',1)) v(r,c,k,p)
union all
select 'jeju_new','제주시',k,2 from unnest(array['노형','연동','외도','이호','도두','내도','도평','해안']) k
union all
select 'jeju_old','제주시',k,2 from unnest(array['일도','이도','삼도','용담','건입','화북','삼양','봉개','아라','오라','오등','도남','영평','월평','용강','회천','도련']) k
union all
select 'seogwipo_dong','서귀포시',k,2 from unnest(array['서귀동','송산','정방','중앙','천지','효돈','영천','동홍','서홍','대륜','법환','보목','토평','상효','하효','신효','호근','서호']) k
union all
select 'jungmun','서귀포시',k,2 from unnest(array['중문','대천','예래','색달','회수','하원','도순','강정','월평','상예','하예','대포','용흥','영남']) k;

-- 주소/지명 문자열 → region_id (시 이름이 있으면 그 시 안에서만 찾는다)
create or replace function refined.region_of(addr text) returns text language sql stable as $$
  select k.region_id from refined.region_keyword k
  where addr like '%' || k.keyword || '%'
    and (k.city = case when addr like '%서귀포%' then '서귀포시' when addr like '%제주시%' then '제주시' else k.city end)
  order by k.prio, length(k.keyword) desc limit 1
$$;

-- 3) 위경도 → region_id: 가장 가까운 버스정류소(612)의 주소로 판별
create or replace view refined.bus_station_geo as
select "stationId" station_id, "stationName" station_name, "stationAddress" address,
       refined.region_of("stationAddress") region_id,
       extensions.st_setsrid(extensions.st_makepoint("longitude"::float, "latitude"::float), 4326)::extensions.geography geog
from raw.hub_612 where "longitude" ~ '^[0-9.]+$';

create table if not exists refined.bus_station_pt as select * from refined.bus_station_geo with no data;
truncate refined.bus_station_pt; insert into refined.bus_station_pt select * from refined.bus_station_geo where region_id is not null;
create index if not exists bus_station_pt_geog on refined.bus_station_pt using gist (geog);

create or replace function refined.region_of_point(lon double precision, lat double precision) returns text language sql stable as $$
  select region_id from refined.bus_station_pt
  order by geog operator(extensions.<->) extensions.st_setsrid(extensions.st_makepoint(lon, lat), 4326)::extensions.geography limit 1
$$;
-- 주소가 '가시리 123'처럼 읍면 없이 리만 있는 정류소(약 680곳)는 가장 가까운 매핑된 정류소의 권역으로 채운다
insert into refined.bus_station_pt
select g.station_id, g.station_name, g.address,
       refined.region_of_point(extensions.st_x(g.geog::extensions.geometry), extensions.st_y(g.geog::extensions.geometry)), g.geog
from refined.bus_station_geo g where g.region_id is null;

-- 4) 지표별 계산
create or replace view refined.m_rent as   -- rent_index: 제주 전체 대비 환산월세(㎡당) 중앙값 비율, 주택유형별 비율을 거래수로 가중평균
with t as (
  select kind, refined.region_of(case lawd_cd when '50110' then '제주시 ' else '서귀포시 ' end || (item->>'umdNm')) region_id,
         (replace(item->>'monthlyRent', ',', '')::numeric + replace(item->>'deposit', ',', '')::numeric * 0.055 / 12)
           / nullif(coalesce(nullif(item->>'excluUseAr',''), item->>'totalFloorAr')::numeric, 0) won_per_m2
  from raw.molit_rent),
island as (select kind, percentile_cont(0.5) within group (order by won_per_m2) med from t group by kind),
reg as (select region_id, kind, count(*) n, percentile_cont(0.5) within group (order by won_per_m2) med from t where region_id is not null group by 1, 2)
select reg.region_id, round((sum(reg.med / island.med * reg.n) / sum(reg.n))::numeric, 2) rent_index, sum(reg.n) rent_samples
from reg join island using (kind) group by reg.region_id;

create or replace view refined.m_bus as     -- bus_stops: 정류소 수 / bus_routes: 기·종점이 그 권역인 노선 수(근사)
select b.region_id, count(distinct b.station_id) bus_stops,
       (select count(distinct r."routeId") from raw.hub_611 r join refined.bus_station_pt s
          on s.station_id in (r."startStationId", r."endStationId") where s.region_id = b.region_id) bus_routes
from refined.bus_station_pt b group by b.region_id;

create or replace view refined.m_amenity as -- amenity_cnt: 상가정보(793) 마트·편의점·카페·세탁
select refined.region_of("시군구명" || ' ' || "행정동명") region_id, count(*) amenity_cnt
from raw.hub_793
where "상권업종소분류명" ~ '(슈퍼마켓|편의점|카페|커피|세탁|빨래)'
group by 1;

create or replace view refined.m_medical as -- hospital_cnt / pediatric_cnt: 병의원(859) 영업 중
select refined.region_of("addressJibun") region_id, count(*) hospital_cnt,
       -- 종합병원·의원은 진료과목을 전부 나열하는 경우가 많아, 과목 4개 이하이면서 소아청소년과가 있거나 이름에 소아·아이·어린이가 있는 곳만
       count(*) filter (where ("medicalSubject" like '%소아%' and array_length(string_to_array("medicalSubject", ','), 1) <= 4)
                           or "companyName" ~ '(소아|아이|어린이)') pediatric_cnt
from raw.hub_859 where "openStatus" like '영업%' group by 1;

create or replace view refined.m_er as      -- er_drive_min: 권역 대표좌표 → 가장 가까운 응급실(1046, 좌표는 상가정보 793 상호명 매칭) 직선거리×1.3, 시속 45km
with er as (
  select distinct on (e."병원명") e."병원명", extensions.st_setsrid(extensions.st_makepoint(s."경도"::float, s."위도"::float), 4326)::extensions.geography g
  from raw.hub_1046 e join raw.hub_793 s on s."상호명" = e."병원명" or s."상호명" like e."병원명" || '%')
select r.region_id, round(min(extensions.st_distance(extensions.st_setsrid(extensions.st_makepoint(r.lon, r.lat), 4326)::extensions.geography, er.g)) / 1000 * 1.3 / 45 * 60) er_drive_min
from refined.regions r cross join er group by r.region_id;

create or replace view refined.m_weather as -- jan_temp / sunshine_jan: 877 일간기후(2000~2021) 1월, 권역마다 가장 가까운 관측소
with st(name, lat, lon) as (values ('제주',33.514,126.530),('고산',33.294,126.163),('성산',33.387,126.880),('서귀포',33.246,126.565)),
jan as (select "관측소" st, avg(trim("Tem_mean")::numeric) t,
               -- 제주 관측소 파일은 일조 값이 0.2시간/일 수준으로 깨져 있어 기상청 평년값 기반 1월 70시간(jeju.com 겨울 팁)을 쓴다
               case when "관측소" = '제주' then 70 else avg(trim("Sunshine_mean")::numeric) * 31 end sun
        from raw.hub_877 where substr("Date", 6, 2) = '01' and trim("Tem_mean") ~ '^-?[0-9.]+$' group by 1),
near as (select distinct on (r.region_id) r.region_id, st.name from refined.regions r cross join st
         order by r.region_id, (r.lat - st.lat)^2 + (r.lon - st.lon)^2)
select near.region_id, near.name weather_station, round(jan.t, 1) jan_temp, round(jan.sun) sunshine_jan
from near join jan on jan.st = near.name;

create or replace view refined.m_crowd as   -- crowd_index: 방문/(거주+방문) 인구 (583, 2025-10)
select refined.region_of("city" || ' ' || "emd") region_id,
       round(sum("visitPop"::numeric) / nullif(sum("resdPop"::numeric) + sum("visitPop"::numeric), 0), 2) crowd_index
from raw.hub_583 group by 1;

create or replace view refined.m_odor as    -- odor_flag: 영업 중 양돈 농가(838) 15곳 이상 또는 악취관리지역 사업장(480) 3곳 이상
with pig as (select refined.region_of("addressJibun") region_id, count(*) n from raw.hub_838
             where "openStatus" like '영업%' and "bizSmallType" like '%돼지%' group by 1),
zone as (select refined.region_of("소재지_(대표주소)") region_id, count(*) n from raw.hub_480 where "구분" = '악취관리지역' group by 1)
select r.region_id, coalesce(pig.n, 0) pig_farms, coalesce(zone.n, 0) odor_zone_sites,
       (coalesce(pig.n, 0) >= 15 or coalesce(zone.n, 0) >= 3)::int odor_flag
from refined.regions r left join pig using (region_id) left join zone using (region_id);

-- 렌터카 체류 지점(1208) → 권역 (지점이 많아 테이블로 1회 계산)
create table if not exists refined.rentcar_stay_by_region (month text, region_id text);
truncate refined.rentcar_stay_by_region;
insert into refined.rentcar_stay_by_region
select substr("collection_dt", 1, 6), refined.region_of_point("longitude"::float, "latitude"::float)
from raw.hub_1208 where "longitude" ~ '^[0-9.]+$';

create or replace view refined.m_extra as   -- 재미 지수 재료 (교차검증 결과는 docs/DATA.md '재미 지수')
with pop as (   -- 583 거주·방문 인구(2025-10, 합계값이라 비율로만 쓴다)
  select refined.region_of("city" || ' ' || "emd") region_id, sum("resdPop"::numeric) resd from raw.hub_583 group by 1),
stay as (select region_id, count(*) n from refined.rentcar_stay_by_region group by 1),
biz as (        -- 830 읍면동 사업체 생멸: 2021~2023 신생 ÷ 활동
  select refined.region_of("시구분" || ' ' || "읍면동") region_id,
         sum("사업체수"::numeric) filter (where "사업체구분" = '신생사업체' and "생멸구분" = '소계')
       / nullif(sum("사업체수"::numeric) filter (where "사업체구분" = '활동사업체' and "생멸구분" = '소계'), 0) new_rate
  from raw.hub_830 where "기준연도" between '2021' and '2023' group by 1),
food as (       -- 780 영업 중 음식점: 2006년 이전 인허가(=20년 이상) 비율
  select refined.region_of("소재지전체주소") region_id, count(*) n, avg(("인허가일자" < '2006')::int) old_ratio
  from raw.hub_780 where "영업상태명" like '영업%' and "인허가일자" ~ '^[0-9]{4}' group by 1)
select r.region_id,
  stay.n rentcar_stays,
  -- 렌터카 습격 지수: 거주 인구당 렌터카 체류 ÷ 제주 평균 (1.0 = 평균, 2.0 = 평균의 두 배)
  round((stay.n / pop.resd) / (select sum(n) from stay) * (select sum(resd) from pop where region_id is not null), 2) rentcar_index,
  (select count(*) from raw.hub_811 o where refined.region_of(o."addressJibun") = r.region_id) oreum_cnt,
  round(food.old_ratio, 3) nopo_ratio, food.n restaurant_cnt,
  round(biz.new_rate, 3) new_biz_rate
from refined.regions r
left join pop using (region_id) left join stay using (region_id) left join biz using (region_id) left join food using (region_id);

-- 5) 최종: 앱이 읽는 형태 그대로. 실데이터가 없는 컬럼은 sample 값(refined.region_metrics_manual)을 쓰고 dummy_cols에 기록
create table if not exists refined.region_metrics_manual (
  region_id text primary key, base_stay_month int, wifi_ap int, cowork_cnt int, inland_heating_risk int, snow_road_flag int);
insert into refined.region_metrics_manual values
 ('jeju_new',115,120,6,0,0),
 ('jeju_old',115,140,4,0,0),
 ('aewol',100,40,2,1,0),
 ('hallim',100,35,1,0,0),
 ('hangyeong',90,20,0,1,0),
 ('jocheon',90,45,2,1,1),
 ('gujwa',90,30,1,1,0),
 ('seongsan',90,30,0,0,0),
 ('pyoseon',90,25,0,1,0),
 ('namwon',90,25,0,0,1),
 ('seogwipo_dong',90,90,3,0,1),
 ('jungmun',90,50,1,0,1),
 ('andeok',90,20,0,0,0),
 ('daejeong',90,30,1,0,0)
on conflict (region_id) do nothing;
-- base_stay_month: refined.manual_stay_price_region 중간값(제주시 115, 서귀포·구좌·성산 90). 애월·한림은 가이드에 금액 없이 '중상급' → 100,
--   나머지 읍면은 금액 근거가 없어 90. wifi_ap/cowork_cnt/inland_heating_risk/snow_road_flag 는 아직 앱 sample 값(수동).

create or replace view refined.region_metrics as
select r.region_id, r.name, r.city, r.zone, r.aliases, r.lat, r.lon,
  m.base_stay_month, coalesce(rent.rent_index, 1.0) rent_index,
  coalesce(bus.bus_stops, 0) bus_stops, coalesce(bus.bus_routes, 0) bus_routes,
  coalesce(am.amenity_cnt, 0) amenity_cnt,
  coalesce(med.hospital_cnt, 0) hospital_cnt, coalesce(med.pediatric_cnt, 0) pediatric_cnt,
  er.er_drive_min, w.jan_temp, w.sunshine_jan, cr.crowd_index,
  m.wifi_ap, m.cowork_cnt, m.inland_heating_risk, od.odor_flag, m.snow_road_flag,
  0 is_dummy,  -- 비용 계산에 쓰는 지표는 실데이터. wifi_ap·cowork_cnt·heating·snow 는 수동 추정값(docs/DATA.md)
  ex.rentcar_stays, ex.rentcar_index, ex.oreum_cnt, ex.nopo_ratio, ex.restaurant_cnt, ex.new_biz_rate,
  od.pig_farms, rent.rent_samples, w.weather_station
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
left join refined.m_extra ex using (region_id);
comment on view refined.region_metrics is '앱용 권역 지표(14행). data/build/export_supabase.py 로 data/processed/region_metrics.csv 생성';
