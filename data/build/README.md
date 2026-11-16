# data/build — 실제 데이터 수집·전처리 (담당: DATA)

여기 있는 스크립트들이 `data/processed/region_metrics.csv` 를 만든다.
완성되면 `.env` 의 `REGION_METRICS_PATH` 를 그 파일로 바꾸면 앱 전체가 실제 데이터로 동작한다.
(컬럼 정의: `docs/DATA.md`)

## 원칙
- **원본(raw)은 커밋하지 않는다.** `data/raw/` 는 `.gitignore` 처리. 특히 대회 제공 엑셀(데이터허브 목록, 센터 예시)은 외부 배포·GitHub 업로드 금지.
- API 키는 `.env` 에만. 코드·노트북에 직접 쓰지 않는다.
- 스크립트 하나 = 지표 묶음 하나. 결과는 `data/interim/<이름>.csv` (region_id 기준) 로 저장하고, 마지막에 `merge.py` 가 합친다.
- 기준 시점(데이터 기간)을 `docs/DATA.md` 에 꼭 적는다 → 기획서 '결과 신뢰성' 점수

## 할 일 (우선순위 순)

| 스크립트 | 만들 컬럼 | 출처 | 상태 |
|---|---|---|---|
| `jejuhub_card.py` | 소비 수준·업종 활성도, `crowd_index` | 제주데이터허브 **748**, 746 (읍면동, 파일) — **대회 필수 데이터** | TODO |
| `jejuhub_lodging.py` | 민박·숙박 공급량 | 데이터허브 **956** 농어촌민박(읍면동), 837 숙박업 | TODO |
| `rent_index.py` | `rent_index` | 국토부 전월세 실거래가 API 15126474(아파트)·15126472(단독다가구)·15126475(오피스텔) — 제주시 50110·서귀포시 50130 (코드 첫 호출 때 검증) | TODO |
| `bus.py` | `bus_stops`, `bus_routes` | 데이터허브 612 / data.go.kr 15074255(정류소)·15074254(노선) | TODO |
| `amenity.py` | `amenity_cnt` | 소상공인 상가(상권)정보 15083033 (위경도, 업종 필터: 마트·편의점·카페·세탁) | TODO |
| `medical.py` | `hospital_cnt`, `pediatric_cnt`, `er_drive_min` | HIRA 병원정보 15001698, 약국 15001673 / 데이터허브 859·861·1046 | TODO |
| `weather.py` | `jan_temp`, `sunshine_jan` | 기상청 ASOS 일자료 15059093 (제주 184·고산 185·성산 188·서귀포 189 — 검증 필요), 읍면은 가장 가까운 관측소 배정 | TODO |
| `wifi_cowork.py` | `wifi_ap`, `cowork_cnt` | 데이터허브 618 공공와이파이 + 워케이션 오피스 수동 목록 | TODO |
| `flags.csv` (수동) | `odor_flag`, `snow_road_flag`, `inland_heating_risk` | 악취관리지역 기사, 1100·5.16도로 통제, 중산간 여부 | TODO |
| `merge.py` | 전체 합치기 → `data/processed/region_metrics.csv` | 위 결과 | TODO |

자세한 출처·한계는 레포 밖 리서치 리포트(노션/프로젝트 문서 「한달살이 고려사항과 데이터」) 참고.
