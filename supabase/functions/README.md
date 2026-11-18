# Supabase Edge Functions — 데이터 수집

모든 함수는 DB 안의 `private.ingest_config`(k='token') 토큰을 `x-ingest-token` 헤더로 확인한다.
제주데이터허브는 해외 IP를 방화벽으로 막기 때문에 **반드시 서울 리전**으로 호출한다(`x-region: ap-northeast-2`).
호출은 DB에서 pg_net으로 한다 → `supabase/sql/00_setup.sql` 의 `private.hub_call / link_call / api_call / molit_call`.

| 함수 | 하는 일 | 필요한 시크릿 |
|---|---|---|
| ingest-jejuhub | 허브 FILE 데이터(csv) 다운로드 → `private.staging` (mode=catalog 이면 `raw._catalog`만 갱신) | – |
| ingest-link | 허브 LINK 데이터 → data.go.kr 파일데이터 페이지에서 파일 다운로드 → `private.staging` | – |
| ingest-hubapi | 허브 Open API(`open.jejudatahub.net/api/proxy/{dataKey}/{KEY}`) 전 페이지 수집 → `raw.hub_{id}` | `JEJU_HUB_KEY` |
| ingest-molit | 국토부 전월세 실거래가(아파트·단독다가구·오피스텔) → `raw.molit_rent` | `DATA_GO_KR_KEY` |

배포: `supabase functions deploy <이름> --no-verify-jwt` (토큰 검사는 함수가 직접 함)
시크릿: `supabase secrets set JEJU_HUB_KEY=... DATA_GO_KR_KEY=...` (Decoding 키, 앞뒤 공백 주의)
