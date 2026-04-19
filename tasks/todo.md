- [x] 오류 메시지와 월 단위 주기 처리 위치 확인
- [x] `PublicDataReader` 호출 전 pandas 월말 주기 호환 처리 추가
- [x] 가능한 범위에서 검증 실행
- [x] Polar Scatter tooltip 직렬화 오류 원인 확인
- [x] `JsCode` tooltip을 JSON 안전한 템플릿 문자열로 변경
- [x] 기간별 거래 추이 차트의 타이틀/legend 간격 확인
- [x] 기간별 거래 추이 차트 상단 여백 조정
- [x] 검증 및 커밋/푸시

## Review
- 원인: `PublicDataReader` 내부에서 pandas 월말 주기 별칭 `m`을 사용하고, pandas 3에서는 이 별칭이 제거되어 `ME` 사용을 요구함.
- 조치: API 호출 구간에서 `pd.date_range(..., freq="m")` 실패 시 `freq="ME"`로 재시도하도록 호환 레이어를 추가하고, 배포 의존성을 `pandas<3`로 고정함.
- 검증: `python3 -m py_compile app.py` 통과.
- 제한: 로컬 Python 환경에 `pandas`와 `PublicDataReader`가 없어 실제 API 호출 재현은 미실행.
- 테스트: 표준 테스트 설정 파일이 없어 미실행.

## Review 2026-04-19
- 원인: `streamlit_echarts.st_pyecharts()`가 `chart.dump_options()` 결과를 `json.loads()`로 파싱하는데, Polar Scatter tooltip의 `JsCode(function...)`가 유효한 JSON이 아니어서 `JSONDecodeError`가 발생함.
- 조치: tooltip formatter를 `JsCode`에서 ECharts 템플릿 문자열로 바꾸고, 거래일을 value 배열의 세 번째 차원으로 전달함.
- 검증: `python3 -m py_compile app.py` 통과.
- 제한: 로컬 Python 환경에 `pandas`, `pyecharts`, `streamlit_echarts`가 없어 실제 Streamlit 렌더링 재현은 미실행.
- 테스트: 표준 테스트 설정 파일이 없어 미실행.

## Review 2026-04-19 Chart Spacing
- 원인: 기간별 거래 추이 차트의 내부 title과 legend가 모두 상단 0~4% 영역에 배치되어 겹침.
- 조치: title은 상단에 두고 legend를 14%로 내리며, grid 시작 위치를 26%로 내려 차트 본문과도 분리함.
- 검증: `python3 -m py_compile app.py` 통과.
- 제한: 로컬 Python 환경에 `pyecharts`가 없어 실제 차트 렌더링 재현은 미실행.
- 테스트: 표준 테스트 설정 파일이 없어 미실행.
