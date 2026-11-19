# 돌몽이 — 예비 도민을 위한 제주살이 동네 추천 AI Agent

제주 AI·빅데이터 활용 AI Agent 개발 챌린지 최종 결과물 · 팀 **돌몽이키우기**

> "1월부터 석 달, 둘이서, 차 없이, 총 900만 원 안에서" 같은 조건을 받아
> 제주 14개 생활권의 **체류 총비용**(숙소·이동·식비·공과금)과 **생활환경**(교통·의료·편의·조용함·자연·날씨·맛집·밤길)을
> 제주데이터허브 데이터로 계산해 동네를 추천하고, 캐릭터 상담 Agent '돌몽이'가 리포트를 같이 읽으며 질문에 답하는 서비스입니다.

- **바로 써 보기 (설치 없이):** https://bang-aeo-hwae.vercel.app
- 처음 들어가면 돌몽이 문답이 뜹니다. 다시 보려면 주소 뒤에 `?start=1` 을 붙이세요.

---

## 이 ZIP 안에 있는 것 (대회 필수 제출 항목 대응표)

| 대회 구분 | 필수 내용 | 이 ZIP 의 위치 |
|---|---|---|
| **실행 소스 코드** | Agent 실행 코드 | `1_실행소스코드/backend/agent/` (상담 Agent `dolmong_agent.py`, 규칙 모드 `consult.py`) |
| | Prompt | `1_실행소스코드/prompts/` (사본 + 원본 위치 표) |
| | Tool/API 연동 및 데이터 처리 코드 | 도구 `backend/tools/`, API 서버 `backend/main.py`, 수집 `supabase/functions/`, 전처리 `supabase/sql/`, 내보내기 `data/build/` |
| | 사용 모델·라이브러리 정보 | `1_실행소스코드/MODELS_AND_LIBRARIES.md`, `requirements.txt` |
| **실행환경·매뉴얼** | README, 설치·실행 절차 | 이 파일 (아래 "설치·실행") |
| | 의존성 목록 | `1_실행소스코드/requirements.txt` |
| | 환경변수 예시 | `1_실행소스코드/.env.example`, 이 파일의 "환경변수" 표 |
| | 사용자 매뉴얼 | `2_실행환경_매뉴얼/사용자매뉴얼.pdf` |
| | 오류·제약사항 | 이 파일의 "자주 나는 오류", "제약사항" |
| **데이터 활용 명세** | 필수 데이터 사용 내역, 출처·이용조건, 전처리·분석 흐름, 외부 데이터·오픈소스 목록 | `3_데이터활용명세/데이터활용명세.pdf` (+ 상세 표 `DATA.md`, `DATA_CATALOG.md`, `COST_MODEL.md`) |
| **결과 설명자료** | 문제 정의, Agent 구조, 주요 기능, 실행 결과, 검증 방법·한계, 센터 활용 방안 | `4_결과설명자료/결과설명자료.pdf` |

각 PDF 와 같은 내용의 `.md` 파일도 함께 들어 있습니다.

---

## 설치·실행

### 요구 사항
- **Python 3.10 이상** (3.13 에서 검증)
- 인터넷: 설치할 때 `pip` 다운로드에만 필요. Claude 키를 넣으면 상담 Agent 가 Anthropic API 를 호출합니다.
- 센터 PC 사양(Intel i7-8700 / GTX 1060 / RAM 32GB)으로 충분합니다. 로컬 LLM 을 쓰지 않고, 데이터는 미리 가공한 CSV(약 50KB)만 읽습니다. GPU 는 쓰지 않습니다.

### Windows (센터 PC 기준)
명령 프롬프트(cmd)에서:
```bat
cd 1_실행소스코드
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn backend.main:app --port 8000
```
브라우저에서 **http://localhost:8000** 을 엽니다. 끌 때는 cmd 창에서 `Ctrl + C`.

### macOS / Linux
```bash
cd 1_실행소스코드
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --port 8000
```

### 두 가지 실행 모드
| 모드 | 조건 | 동작 |
|---|---|---|
| **Claude Agent 모드** | `.env` 의 `ANTHROPIC_API_KEY` 에 키를 넣음 | 상담창 자유 질문을 Claude 가 해석해 도구 7개를 골라 쓰고, 필요하면 리포트 수정을 제안 |
| **규칙 + 데이터 모드** | 키를 비워 둠 (기본) | 같은 도구·데이터를 정규식 분류로 호출해 답함. 추천·리포트·빠른 버튼은 두 모드가 똑같음 |

지금 모드는 http://localhost:8000/api/health 의 `agent_mode` 값(`claude` / `mock`)이나 상담창 제목 옆 표시("기본 모드")로 확인합니다.

### 평가용 Claude 키
- 평가용 키는 대회 규정에 따라 **사용 한도를 걸고** 제출하며, 평가가 끝나면 폐기합니다.
- 평가용 키가 들어 있으면 `1_실행소스코드/.env.example` 의 `ANTHROPIC_API_KEY=` 뒤에 적혀 있고, `.env` 로 복사하면 바로 Claude Agent 모드로 실행됩니다. 비어 있으면 규칙 + 데이터 모드로 실행되며, 직접 발급한 키를 넣어도 됩니다(https://console.anthropic.com).
- 키가 한도에 걸리거나 만료되어도 서비스는 멈추지 않고 규칙 + 데이터 모드로 답합니다.

### 테스트
```bash
python -m pytest -q        # 22 passed
```
`tests/test_agent.py` 는 가짜 Claude 응답으로 도구 루프(여러 도구 동시 호출, 도구 오류 복구, 리포트 수정 제안)를 키 없이 검증합니다.

---

## 환경변수 (`.env`)

| 이름 | 기본값 | 설명 | 실행에 필요? |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | (비어 있음) | Claude API 키. 비우면 규칙 + 데이터 모드 | 선택 |
| `CLAUDE_MODEL` | `claude-haiku-5-5` | 상담 Agent 모델 | 선택 |
| `AGENT_MODE` | `auto` | `auto`(키 있으면 claude) / `claude` / `mock` | 선택 |
| `AGENT_MAX_TURNS` | `5` | 질문 하나에 도구 호출 루프 최대 횟수 | 선택 |
| `AGENT_MAX_TOKENS` | `1500` | 답 한 번의 최대 토큰 | 선택 |
| `AGENT_TIMEOUT` | `25` | API 한 번 기다리는 초 | 선택 |
| `AGENT_RATE_PER_MIN` | `8` | IP 하나가 1분에 보낼 수 있는 자유 질문 수 | 선택 |
| `DOLMONG_DIALECT` | `1` | 돌몽이 대사 끝 어미를 제주어로 (`0` 이면 표준어) | 선택 |
| `REGION_METRICS_PATH` | `data/processed/region_metrics.csv` | 동네 지표 파일 | 선택 |
| `DATA_GO_KR_KEY` (Supabase 시크릿) | – | 공공데이터포털 인증키 — 데이터를 다시 만들 때 `ingest-molit` 이 읽음 | 아니오 |
| `JEJU_HUB_KEY` (Supabase 시크릿) | – | 제주데이터허브 API 키 — 데이터를 다시 만들 때 Edge Function `ingest-hubapi` 가 읽음 | 아니오 |
| `SUPABASE_DB_URL` | (비어 있음) | Supabase 연결 문자열 — 데이터를 다시 내보낼 때만 | 아니오 |

**데이터 API 키는 제출물에 넣지 않았습니다** (대회 규정). 발급 방법:
- 제주데이터허브: https://www.jejudatahub.net 회원가입 → 마이페이지 → 프로젝트 생성 → 데이터를 프로젝트에 담기 → 프로젝트 API 키 발급
- 공공데이터포털: https://www.data.go.kr 회원가입 → 국토교통부 아파트·단독다가구·오피스텔 전월세 실거래가(15126474·15126472·15126475) 활용신청 → 마이페이지의 일반 인증키(Decoding)

---

## 데이터를 처음부터 다시 만들려면 (선택)
실행에는 필요 없습니다. `data/processed/*.csv` 에 가공 결과가 이미 들어 있습니다.
1. Supabase 프로젝트를 **서울 리전**으로 만들고 `supabase/sql/00_setup.sql` 실행 (제주데이터허브가 해외 IP 를 막음)
2. `supabase/functions/` 의 함수 4개 배포, 시크릿 `JEJU_HUB_KEY`, `DATA_GO_KR_KEY` 등록 (방법: `supabase/functions/README.md`)
3. `10_ingest.sql` → `20_region_metrics.sql` → `25`~`29` → `30_care_points.sql` 순서로 실행
4. `.env` 에 `SUPABASE_DB_URL` 을 넣고 `pip install "psycopg[binary]"` 후 `python -m data.build.export_supabase`

자세한 흐름은 `3_데이터활용명세/데이터활용명세.pdf` 의 "전처리·분석 흐름" 참고.

---

## 자주 나는 오류

| 증상 | 원인 | 해결 |
|---|---|---|
| `'python'은(는) 내부 또는 외부 명령...` | Python 미설치 또는 PATH 미등록 | python.org 에서 3.10 이상 설치, 설치 첫 화면에서 "Add python.exe to PATH" 체크 |
| `.venv\Scripts\activate` 가 PowerShell 에서 막힘 | 실행 정책 | cmd 를 쓰거나, PowerShell 에서 `Set-ExecutionPolicy -Scope Process RemoteSigned` |
| `[Errno 10048] ... address already in use` | 8000 포트 사용 중 | `uvicorn backend.main:app --port 8001` 후 http://localhost:8001 |
| `ModuleNotFoundError: No module named 'backend'` | 다른 폴더에서 실행 | `1_실행소스코드` 폴더 안에서 실행 |
| 상담창에 "기본 모드" 표시 | 키 없음, 키 한도 초과, API 오류 | 정상 동작입니다. Claude 모드를 원하면 `.env` 의 키 확인 후 서버 재시작 |
| "질문이 많아서 잠깐 기본 모드로 답했어요" | IP 당 1분 8개 제한 | 1분 뒤 다시 질문, 또는 `AGENT_RATE_PER_MIN` 을 늘림 |
| 동네 사진이 회색, 글꼴이 다름 | 인터넷 차단으로 위키미디어 사진·Pretendard CDN 을 못 불러옴 | 기능에는 영향 없음 |
| 첫 화면 문답이 안 뜸 | 이미 한 번 봤음 (브라우저에 저장) | 주소 뒤에 `?start=1` |

## 제약사항
- **비용은 추정치입니다.** 숙소 권역 기준가·렌터카·식비 단가는 공개 가이드 기반 가정값이고, 동네 간 차이는 국토부 전월세 실거래가 임대지수로 반영합니다. 화면의 ±15% 범위는 통계적 신뢰구간이 아닙니다.
- **데이터 시점이 서로 다릅니다.** 기후 2000~2021, 렌터카 체류 2021 하반기, 유동인구 2025-10, 상가·병원 2025-09, 전월세 2025-11~2026-10.
- **비교 단위는 14개 생활권**(읍·면, 제주시·서귀포시 동지역 묶음)입니다. 마을·건물 단위 추천은 하지 않습니다.
- 교통·편의·안전 점수는 정류장 수, 시설 수, CCTV 수 같은 **대리 지표**입니다. 버스 시간표·배차, 실제 매물, 계약·전입 같은 행정 정보는 제공하지 않고 공식 문의처(제주120만덕콜센터 등)를 안내합니다.
- Claude Agent 모드는 외부 API 라서 답에 몇 초가 걸리고, 드물게 질문 의도를 잘못 읽을 수 있습니다. 숫자는 도구 결과만 쓰도록 막아 두었고, 답마다 "돌몽이가 확인한 것"(호출한 도구)과 참고 데이터를 함께 보여 줍니다.
- 사용량 제한(IP 당 1분 8개)은 서버 메모리 기준이라 서버가 다시 시작되면 초기화됩니다. 최종 비용 상한은 Anthropic 콘솔의 사용 한도로 막습니다.

---

## 폴더 구조
```
돌몽이키우기_최종결과물/
├─ README.md                      ← 지금 이 파일 (실행환경·매뉴얼)
├─ 1_실행소스코드/
│  ├─ backend/                    FastAPI 서버, Agent, 도구
│  │  ├─ main.py                  API (/api/estimate, /api/consult, /api/rehearsal ...)
│  │  ├─ agent/dolmong_agent.py   ★ 돌몽이 상담 Agent (Claude tool-use 루프)
│  │  ├─ agent/consult.py         규칙 + 데이터 모드 (LLM 없이)
│  │  └─ tools/                   비용·점수·지수·리허설·근거 계산 (순수 파이썬)
│  ├─ frontend/                   화면 (HTML/CSS/JS, 빌드 없음)
│  ├─ data/processed/             가공된 동네 데이터 CSV (실행 시 읽는 파일)
│  ├─ supabase/                   데이터 수집 함수 + 전처리 SQL
│  ├─ data/build/                 Supabase → CSV 내보내기
│  ├─ prompts/                    프롬프트 사본
│  ├─ tests/                      pytest 22개
│  ├─ docs/                       DATA.md, COST_MODEL.md, DATA_CATALOG.md
│  ├─ MODELS_AND_LIBRARIES.md     사용 모델·라이브러리·외부 서비스
│  ├─ README_개발자.md            팀 내부 개발 가이드
│  ├─ requirements.txt, .env.example, index.py(Vercel 진입점)
├─ 2_실행환경_매뉴얼/  사용자매뉴얼.pdf (.md)
├─ 3_데이터활용명세/   데이터활용명세.pdf (.md), DATA.md, DATA_CATALOG.md, COST_MODEL.md
└─ 4_결과설명자료/     결과설명자료.pdf (.md)
```

## 팀·라이선스
- 팀: 돌몽이키우기
- 캐릭터 돌몽이: 팀 자체 제작
- 대회 규정에 따라 결과물의 권리는 제주빅데이터센터에 귀속됩니다.
