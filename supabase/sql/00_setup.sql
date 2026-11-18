-- =====================================================================
-- 00_setup.sql — 새 Supabase 프로젝트에서 한 번 실행
-- 스키마: raw(원본, 모든 컬럼 text) / refined(서비스용 정제·지표) / reviews(구글 리뷰) / private(내부 설정)
-- =====================================================================
create extension if not exists pg_net;
create extension if not exists postgis with schema extensions;

create schema if not exists raw;
create schema if not exists refined;
create schema if not exists reviews;
create schema if not exists private;
revoke all on schema raw, refined, reviews, private from anon, authenticated;
comment on schema raw is '제주데이터허브·공공데이터 원본 (모든 컬럼 text, hub_{데이터ID})';
comment on schema refined is '서비스용 정제 데이터와 지표';
comment on schema reviews is '구글 리뷰 데이터(제주데이터허브 901~906). *_raw=원천 리뷰(작성자 이름 제거), *_monthly=장소별 월간 평점·리뷰수';

-- 수집 함수 호출 설정: 함수 URL과 호출 토큰(무작위). 토큰은 DB 밖으로 내보내지 않는다.
create table if not exists private.ingest_config (k text primary key, v text not null);
insert into private.ingest_config values ('token', encode(extensions.gen_random_bytes(24), 'hex')) on conflict do nothing;
-- ↓ 본인 프로젝트 ref 로 바꿀 것
insert into private.ingest_config values ('functions_url', 'https://<project-ref>.supabase.co/functions/v1') on conflict do nothing;

-- 데이터 번호 ↔ 이름 매칭표 (raw._catalog) 와 적재 기록
create table if not exists raw._catalog (
  data_id int primary key, title text, category text, data_type text, period text, owner text, description text,
  csv_files int, other_files text, total_mb numeric, table_name text, status text, hub_url text,
  row_count bigint, updated_at timestamptz default now());
comment on table raw._catalog is '제주데이터허브 데이터 번호 ↔ 이름 매칭표. hub_{data_id} 테이블과 연결';

create table if not exists raw._ingest_log (
  id bigserial primary key, data_id int not null, title text, table_name text, file_name text,
  file_size bigint, encoding text, row_count int, loaded_at timestamptz default now());

create table if not exists raw.molit_rent (id bigserial primary key, kind text, lawd_cd text, deal_ym text, item jsonb, loaded_at timestamptz default now());
create index if not exists molit_rent_k on raw.molit_rent (kind, lawd_cd, deal_ym);

-- 다운로드된 CSV 원문 임시 보관 (적재 후 삭제)
create table if not exists private.staging (
  id bigserial primary key, data_id int, title text, period text, file_name text, encoding text,
  file_size bigint, content text, created_at timestamptz default now());

-- CSV 한 줄 → text[] (따옴표 안 쉼표 처리). 따옴표 안 줄바꿈은 지원하지 않음 → 적재 후 검사 쿼리로 확인
create or replace function private.csv_fields(line text) returns text[] language sql immutable as $$
  select coalesce(array_agg(case when m[1] like '"%' then replace(substr(m[1],2,length(m[1])-2),'""','"') else m[1] end order by ord), '{}')
  from regexp_matches(',' || line, ',("(?:[^"]|"")*"|[^,]*)', 'g') with ordinality as t(m, ord)
$$;

-- staging 한 건 → raw.hub_{data_id}. p_reset=true 면 테이블을 새로 만든다(그 데이터의 첫 파일).
-- 파일마다 헤더가 다르면 컬럼을 합집합으로 늘린다. 모든 값은 text, 빈 문자열은 null.
create or replace function private.load_staged(p_staging_id bigint, p_reset boolean) returns int language plpgsql as $$
declare s private.staging; hdr text[]; cols text[] := '{}'; c text; i int; n int; tbl text; used text[] := array['_row_id','_source_file'];
begin
  select * into s from private.staging where id = p_staging_id;
  tbl := 'hub_' || s.data_id;
  hdr := private.csv_fields(split_part(replace(s.content, E'\r', ''), E'\n', 1));
  for i in 1..coalesce(array_length(hdr,1),0) loop
    c := regexp_replace(trim(replace(coalesce(hdr[i],''), E'﻿','')), '[\s."]+', '_', 'g');
    if c = '' then c := 'col_' || i; end if;
    while octet_length(c) > 60 loop c := left(c, length(c)-1); end loop;
    if c = any(used) then c := c || '_' || i; end if;
    used := used || c; cols := cols || c;
  end loop;
  if p_reset then
    execute format('drop table if exists raw.%I', tbl);
    delete from raw._ingest_log where data_id = s.data_id;
  end if;
  execute format('create table if not exists raw.%I (_row_id bigserial primary key, _source_file text)', tbl);
  foreach c in array cols loop execute format('alter table raw.%I add column if not exists %I text', tbl, c); end loop;
  execute format('comment on table raw.%I is %L', tbl, s.title || ' (제주데이터허브 ID ' || s.data_id || ', 수집기간 ' || s.period || ')');
  execute format(
    'insert into raw.%I (_source_file, %s) select $1, %s from (select private.csv_fields(l) f from unnest(string_to_array(replace($2, E''\r'', ''''), E''\n'')) with ordinality u(l, o) where o > 1 and btrim(l, '', '') <> '''') x',
    tbl,
    (select string_agg(format('%I', x), ', ' order by o) from unnest(cols) with ordinality t(x, o)),
    (select string_agg(format('nullif(f[%s], '''')', o), ', ' order by o) from unnest(cols) with ordinality t(x, o)))
  using s.file_name, s.content;
  get diagnostics n = row_count;
  insert into raw._ingest_log (data_id, title, table_name, file_name, file_size, encoding, row_count)
    values (s.data_id, s.title, tbl, s.file_name, s.file_size, s.encoding, n);
  delete from private.staging where id = p_staging_id;
  return n;
end $$;

-- 수집 함수 호출 (pg_net, 비동기). 데이터허브가 해외 IP를 막으므로 x-region 으로 서울 리전 고정.
create or replace function private._call(fn text, body jsonb, timeout_ms int default 150000) returns bigint language sql as $$
  select net.http_post(
    url := (select v from private.ingest_config where k = 'functions_url') || '/' || fn,
    body := body,
    headers := jsonb_build_object('Content-Type', 'application/json', 'x-region', 'ap-northeast-2',
                                  'x-ingest-token', (select v from private.ingest_config where k = 'token')),
    timeout_milliseconds := timeout_ms);
$$;
create or replace function private.hub_call(body jsonb) returns bigint language sql as $$ select private._call('ingest-jejuhub', body) $$;
create or replace function private.link_call(p_id int) returns bigint language sql as $$ select private._call('ingest-link', jsonb_build_object('data_id', p_id)) $$;
create or replace function private.api_call(body jsonb) returns bigint language sql as $$ select private._call('ingest-hubapi', body) $$;
create or replace function private.molit_call(p_kind text, p_lawd text, p_ym text) returns bigint language sql as $$
  select private._call('ingest-molit', jsonb_build_object('kind', p_kind, 'lawd', p_lawd, 'ym', p_ym), 60000) $$;
revoke all on all functions in schema private from public, anon, authenticated;
