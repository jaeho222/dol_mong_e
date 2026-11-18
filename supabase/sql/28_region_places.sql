-- 한 달 살기 리허설용: 동네별 실제 장소 이름 (지어내지 않기 위해 데이터에서만 뽑는다)
--   cafe/food : 906 구글 음식점 리뷰 × 780 (refined.food_place), 리뷰 20건↑, 평점순 상위 4
--   oreum     : 811 오름 위치 → 905 구글 관광지 리뷰 수로 유명한 순 상위 3
--   camping   : 810 캠핑 장소 (상위 2), library: 888 공공도서관, market: 985 서귀포시 전통시장
create or replace view refined.region_places as
with food as (
  select region_id, case when name ~* '카페|커피|cafe|coffee|베이커리|빵|브루|로스터' then 'cafe' else 'food' end kind,
         name, rating::numeric rating, reviews::int reviews
  from refined.food_place where reviews::int >= 20 and region_id is not null
), food_rk as (
  select *, row_number() over (partition by region_id, kind order by rating desc, reviews desc) rk from food
), o as (
  select coalesce(refined.region_of("addressJibun"), refined.region_of_point(longitude::float8, latitude::float8)) region_id,
         "placeName" name from raw.hub_811
), att as (select place_name, max(review_count::numeric) rc from reviews.attraction_monthly group by 1),
o_s as (
  select o.region_id, o.name, coalesce(max(att.rc), 0) rc
  from o left join att on length(o.name) >= 3 and att.place_name like '%' || o.name || '%'
  group by 1, 2
), o_rk as (select *, row_number() over (partition by region_id order by rc desc, length(name)) rk from o_s),
camp as (
  select coalesce(refined.region_of("addressJibun"), refined.region_of_point(longitude::float8, latitude::float8)) region_id,
         "placeName" name from raw.hub_810
), camp_rk as (select *, row_number() over (partition by region_id order by name) rk from camp)
select region_id, kind, name, rating, reviews from food_rk where rk <= 4
union all select region_id, 'oreum', name, null, rc::int from o_rk where rk <= 3 and region_id is not null
union all select region_id, 'camping', name, null, null from camp_rk where rk <= 2 and region_id is not null
union all select refined.region_of("주소"), 'library', "도서관명", null, null from raw.hub_888
union all select refined.region_of("주소"), 'market', "시장명", null, null from raw.hub_985;
