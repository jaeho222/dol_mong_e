# region_metrics.csv 스키마

Agent와 계산 도구가 보는 **유일한 데이터 테이블**. 행 = 비교 단위 지역(현재 14곳), 열 = 지표.
지금 값은 전부 **더미**(`is_dummy=1`). 실제 값으로 바꾸는 방법은 `data/build/README.md`.

| 컬럼 | 의미 | 단위 | 실제 출처 (예정) | 기준 시점 |
|---|---|---|---|---|
| region_id | 지역 키 (영문) | – | 고정 | – |
| name / city / zone | 표시 이름 / 시 / 권역 | – | 고정 | – |
| aliases | 별칭 (`\|`로 구분) — 자연어 매칭용 | – | 수동 | – |
| lat, lon | 대표 좌표 | WGS84 | 수동 | – |
| base_stay_month | 1인 단기숙소 월 기준가(권역) | 만원 | 리서치 리포트 권역 가격대 + 매물 표본 | TBD |
| rent_index | 제주 평균 대비 임대 상대지수 | 배 | 국토부 전월세 실거래가 | TBD |
| bus_stops / bus_routes | 정류장 수 / 경유 노선 수 | 개 | 데이터허브 612, data.go.kr 15074255·15074254 | TBD |
| amenity_cnt | 마트·편의점·카페·세탁 수 | 개 | 상가(상권)정보 15083033 | TBD |
| hospital_cnt / pediatric_cnt | 병의원 / 소아과 수 | 개 | HIRA 15001698 / 데이터허브 859 | TBD |
| er_drive_min | 가장 가까운 응급실까지 차량 시간 | 분 | 데이터허브 1046 + 거리 계산 | TBD |
| jan_temp / sunshine_jan | 1월 평균기온 / 1월 일조시간 | ℃ / 시간 | 기상청 ASOS 15059093 | TBD |
| crowd_index | 거주 대비 방문 인구 비율 (높을수록 붐빔) | 0~1 | 데이터허브 583·748 | TBD |
| wifi_ap / cowork_cnt | 공공와이파이 AP / 공유오피스 수 | 개 | 데이터허브 618 / 워케이션 오피스 목록 | TBD |
| inland_heating_risk | 중산간·기름보일러 가능성 | 0/1 | 수동 | – |
| odor_flag | 축산 악취 민원 지역 | 0/1 | 기사 기반 수동 | – |
| snow_road_flag | 폭설 시 산간도로 통제 영향 | 0/1 | 수동 | – |
| is_dummy | 더미 값 포함 여부 | 0/1 | merge.py가 자동 계산 | – |

## 컬럼 추가 체크리스트
1. CSV에 컬럼 추가 (sample + build 스크립트)
2. `backend/tools/data_loader.py` 의 `REQUIRED_COLUMNS`
3. 점수에 쓰면 `backend/tools/region.py` 의 `LIVING_METRICS` / `_badges`
4. 이 표에 한 줄
