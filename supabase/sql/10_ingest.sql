-- =====================================================================
-- 10_ingest.sql — 데이터 수집 (SQL Editor 에서 단계별로 실행)
-- pg_net 호출은 비동기라서 각 단계 후 1~2분 기다렸다가 다음 단계를 실행한다.
-- 진행 확인:  select id, status_code, left(content, 300) from net._http_response order by id desc limit 30;
-- 대용량(743·569·746·1213~1216)은 받지 않는다 → 다른 데이터로 대체 (docs/DATA.md '대체·제외')
-- =====================================================================

-- [1] 카탈로그 등록 (번호 ↔ 이름, 형식, 파일 수·크기)
select private.hub_call(jsonb_build_object('data_id', id, 'mode', 'catalog')) from unnest(array[
  -- FILE
  495,512,520,521,523,748,761,780,783,784,793,807,819,830,840,843,846,855,857,877,878,888,
  901,902,903,904,905,906,910,920,931,933,956,965,974,985,1003,1004,1046,1048,1208,1352,1355,
  -- LINK (공공데이터포털)
  35,53,66,99,131,144,163,201,211,216,249,288,340,346,352,356,364,435,436,445,465,466,467,472,476,480,491,506,509,510,517,542,1309,1311,1332,1335,
  -- API (허브 마이페이지 프로젝트에 담아야 호출 가능)
  583,590,611,612,810,811,812,838,859,863
]) id;

-- [2] FILE: 모든 csv 를 staging 으로
select c.data_id, private.hub_call(jsonb_build_object('data_id', c.data_id, 'file_index', i))
from raw._catalog c, generate_series(0, c.csv_files - 1) i
where c.data_type = 'FILE' or c.data_id = 888;

-- [3] LINK: 공공데이터포털 파일 → staging (파일 없이 API만 있는 페이지는 422로 실패, 정상)
select private.link_call(data_id) from raw._catalog where data_type = 'LINK';

-- [4] staging → raw.hub_{id}  (데이터마다 첫 파일만 reset=true, 순서대로 실행해야 함)
do $$ declare r record; begin
  for r in select id, data_id, row_number() over (partition by data_id order by id) rn from private.staging order by data_id, id loop
    perform private.load_staged(r.id, r.rn = 1);
  end loop;
end $$;

-- [5] 허브 API (시크릿 JEJU_HUB_KEY 필요). 유동인구는 2025-10 한 달만
select private.api_call(jsonb_build_object('data_id', id)) from unnest(array[611,612,810,811,812,838,859,863]) id;
select private.api_call('{"data_id":583,"params":{"startDate":"20251001","endDate":"20251031"}}');
select private.api_call('{"data_id":590,"params":{"startDate":"20251001","endDate":"20251031"}}');

-- [6] 국토부 전월세 실거래가 12개월 × 3종 × 제주시·서귀포시 (시크릿 DATA_GO_KR_KEY 필요, 72회 호출)
select private.molit_call(k, l, to_char(m, 'YYYYMM'))
from unnest(array['apt','sh','offi']) k, unnest(array['50110','50130']) l,
     generate_series('2025-11-01'::date, '2026-10-01'::date, '1 month') m;

-- [7] 원본별 보정 (적재 후 1회)
-- 956: 민박명 안에 줄바꿈이 있어 한 행이 둘로 갈라진 건 1건 합치기
update raw.hub_956 set "민박명" = '찔레꽃남쪽마을 민박', "소재지" = '제주시 한림읍 명월로 56', "데이터기준일" = '20211123'
 where "민박명" = '찔레꽃남쪽마을' and "소재지" is null;
delete from raw.hub_956 where "읍면동" = '민박"';
-- 877: 관측소가 파일명에만 있어 컬럼으로
alter table raw.hub_877 add column if not exists "관측소" text;
update raw.hub_877 set "관측소" = case when _source_file like '%제주.csv' then '제주' when _source_file like '%고산.csv' then '고산'
                                      when _source_file like '%성산.csv' then '성산' when _source_file like '%서귀포.csv' then '서귀포' end;
-- 904~906: 헤더 없는 파일이라 첫 행이 컬럼명이 됨 → 그 행을 되살리고 컬럼명 부여, 리뷰 원천은 작성자 이름 삭제 후 reviews 스키마로
do $$ declare t text; c text[]; begin
  foreach t in array array['hub_904','hub_905','hub_906'] loop
    select array_agg(column_name::text order by ordinal_position) into c from information_schema.columns
      where table_schema = 'raw' and table_name = t and column_name not in ('_row_id', '_source_file');
    execute format('insert into raw.%I (_source_file, %I, %I, %I, %I, %I, %I) select _source_file, %L, %L, %L, %L, %L, %L from raw.%I order by _row_id limit 1',
      t, c[1], c[2], c[3], c[4], c[5], c[6], c[1], c[2], replace(c[3], '_', '.'), c[4], c[5], c[6], t);
    execute format('alter table raw.%I rename column %I to place_name', t, c[1]);
    execute format('alter table raw.%I rename column %I to metric', t, c[2]);
    execute format('alter table raw.%I rename column %I to avg_rating', t, c[3]);
    execute format('alter table raw.%I rename column %I to review_count', t, c[4]);
    execute format('alter table raw.%I rename column %I to base_date', t, c[5]);
    execute format('alter table raw.%I rename column %I to weekday', t, c[6]);
  end loop;
end $$;
alter table raw.hub_901 drop column if exists name;
alter table raw.hub_902 drop column if exists name;
alter table raw.hub_903 drop column if exists name;
alter table raw.hub_901 set schema reviews; alter table reviews.hub_901 rename to lodging_raw;
alter table raw.hub_902 set schema reviews; alter table reviews.hub_902 rename to attraction_raw;
alter table raw.hub_903 set schema reviews; alter table reviews.hub_903 rename to restaurant_raw;
alter table raw.hub_904 set schema reviews; alter table reviews.hub_904 rename to lodging_monthly;
alter table raw.hub_905 set schema reviews; alter table reviews.hub_905 rename to attraction_monthly;
alter table raw.hub_906 set schema reviews; alter table reviews.hub_906 rename to restaurant_monthly;

-- [8] 따옴표 안 줄바꿈 등으로 행이 갈라졌는지 검사 (결과가 비어 있어야 정상)
do $$ declare t text; c text; n bigint; begin
  create temp table if not exists _chk(tbl text, col text, n bigint); truncate _chk;
  for t, c in select table_name, column_name from information_schema.columns
              where table_schema = 'raw' and table_name like 'hub_%' and column_name not in ('_row_id', '_source_file') loop
    execute format('select count(*) from raw.%I where %I ~ ''^[^"]*"$'' or %I ~ ''^"[^"]*$''', t, c, c) into n;
    if n > 0 then insert into _chk values (t, c, n); end if;
  end loop;
end $$;
select * from _chk;

-- [9] 카탈로그 상태 갱신
update raw._catalog c set table_name = 'raw.hub_' || c.data_id, status = '적재완료',
  row_count = (select sum(row_count) from raw._ingest_log l where l.data_id = c.data_id), updated_at = now()
where exists (select 1 from raw._ingest_log l where l.data_id = c.data_id) and c.data_id not between 901 and 906;
