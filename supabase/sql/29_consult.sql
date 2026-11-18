-- 돌몽이 상담(규칙 기반)용: 동네별 장소·시설 목록. 데이터에 있는 것만 답하기 위해 한 뷰로 모은다.
-- 새로 적재: 1349 VISIT JEJU 여행장소, 912 관광상품[관광지] 구매·평점(hub_912, hub_912_grad), 25 레저사업체, 162 신고체육시설업(시 단위 집계라 참고만)
-- 909 Place 정보는 허브에 샘플 xlsx 만 있어 제외.

-- 관광지 인기: 912 티켓 구매(아이 동반 비율) + 912 평점(유형) + 905 구글 리뷰 수
create or replace view refined.attraction as
with t as (  -- 912 구매: '자유이용권(카멜리아힐)' → 카멜리아힐
  select trim(coalesce(substring("TRRSRT_NM" from '\(([^)]+)\)'), "TRRSRT_NM")) name,
         "TRRSRT_ADRES" addr, refined.num("ADULT_NMPR_CO") a, refined.num("CHILD_NMPR_CO") + refined.num("INFNT_NMPR_CO") k
  from raw.hub_912
), tk as (
  select name, max(addr) addr, count(*) buys, sum(k) / nullif(sum(a) + sum(k), 0) child_share from t group by 1
), g as (
  select trim("TRRSRT_NM") name, max("TRRSRT_TY_NM") ty, avg(refined.num("EVL_SCORE_VALUE")) score, count(*) n,
         max("TRRSRT_ADRES") addr, max(refined.num("TRRSRT_LO_YCRD")) lon, max(refined.num("TRRSRT_LA_XCRD")) lat
  from raw.hub_912_grad group by 1
), rv as (select place_name, max(review_count::numeric) rc from reviews.attraction_monthly group by 1),
v as (  -- 1349 VISIT JEJU 여행장소 (제주 주소만)
  select distinct on ("장소명") "장소명" name, coalesce("지번주소", "도로명주소") addr, refined.num("경도") lon, refined.num("위도") lat
  from raw.hub_1349 where coalesce("지번주소", "도로명주소") like '제주%'
)
select coalesce(refined.region_of(coalesce(tk.addr, g.addr, v.addr)),
                case when coalesce(g.lon, v.lon) > 0 then refined.region_of_point(coalesce(g.lon, v.lon), coalesce(g.lat, v.lat)) end) region_id,
       coalesce(tk.name, g.name, v.name) name, g.ty, tk.buys, round(tk.child_share::numeric, 2) child_share,
       round(g.score::numeric, 1) score, rv.rc reviews, coalesce(tk.addr, g.addr, v.addr) addr
from tk full join g on g.name = tk.name
full join v on v.name = coalesce(tk.name, g.name)
left join rv on rv.place_name = coalesce(tk.name, g.name, v.name)
where tk.name is not null or g.name is not null or rv.rc >= 30;

-- 상담에서 쓰는 장소 목록 (kind 별)
create or replace view refined.consult_places as
select refined.region_of(coalesce("addressJibun", "addressDoro")) region_id, 'hospital' kind, "companyName" name,
       "bizSmallType" sub, coalesce("addressDoro", "addressJibun") addr,
       case when "medicalSubject" ~ '소아' then 'kids' end extra
from raw.hub_859 where "openStatus" ~ '영업|정상'
union all select refined.region_of("주소"), 'er', "병원명", "병원_유형", "주소", "대표전화" from raw.hub_1046
union all select refined.region_of("소재지"), 'night_pharmacy', "약국명", "운영요일", "소재지", "운영종료시간" from raw.hub_216
union all select coalesce(refined.region_of("addressJibun"), refined.region_of_point(longitude::float8, latitude::float8)), 'museum', "placeName", category, coalesce("addressDoro", "addressJibun"), null from raw.hub_812
union all select refined.region_of("주소"), 'playground', "놀이시설명", null, "주소", null from raw.hub_352
union all select refined.region_of("소재지"), 'playground', "공원명", null, "소재지", null from raw.hub_201
union all select refined.region_of("소재지"), 'leisure', "업체명", "구분", "소재지", "연락처" from raw.hub_25
union all select refined.region_of("소재지"), 'minbak', "민박명", null, "소재지", null from raw.hub_956
union all select coalesce(refined.region_of("지번주소"), refined.region_of_point(refined.num("경도"), refined.num("위도"))), 'amenity:' || "상권업종소분류명",
       "상호명", "상권업종중분류명", coalesce("도로명주소", "지번주소"), null
from raw.hub_793 where "상권업종소분류명" in ('세탁소','셀프 빨래방','헬스장','요가/필라테스 학원','수영장','약국','슈퍼마켓','편의점','독서실/스터디 카페','목욕탕/사우나','동물병원','빵/도넛','볼링장','애완동물/애완용품 소매업');

-- 숙소: 910 예약 기록에서 숙소별 1박 평균 금액
create or replace view refined.lodging as
select refined.region_of("STAYNG_ADRES") region_id, "STAYNG_NM" name, max("STAYNG_TY_NM") ty,
       count(*) bookings, round(avg(refined.num("TOT_AMOUNT") / nullif(refined.num("USE_DAYCNT_CO"), 0))) per_night,
       max("STAYNG_THEMA_NM") thema
from raw.hub_910 where "CANCL_DT" is null and refined.num("TOT_AMOUNT") > 0
group by 1, 2;
