- [x] 오류 메시지와 월 단위 주기 처리 위치 확인
- [x] `PublicDataReader` 호출 전 pandas 월말 주기 호환 처리 추가
- [x] 가능한 범위에서 검증 실행

## Review
- 원인: `PublicDataReader` 내부에서 pandas 월말 주기 별칭 `m`을 사용하고, pandas 3에서는 이 별칭이 제거되어 `ME` 사용을 요구함.
- 조치: API 호출 구간에서 `pd.date_range(..., freq="m")` 실패 시 `freq="ME"`로 재시도하도록 호환 레이어를 추가하고, 배포 의존성을 `pandas<3`로 고정함.
- 검증: `python3 -m py_compile app.py` 통과.
- 제한: 로컬 Python 환경에 `pandas`와 `PublicDataReader`가 없어 실제 API 호출 재현은 미실행.
- 테스트: 표준 테스트 설정 파일이 없어 미실행.
