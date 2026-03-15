# API 테스트 리포트

## 실행 정보
- 테스트 대상 Base URL: `https://petstore.swagger.io/v2`
- 명세 파일 경로: `D:/jhseo/project/swagger-api/swagger/discovered_openapi.json`
- 명세 원본 위치: `https://petstore.swagger.io/v2/swagger.json`
- 명세 확보 방식: `direct`
- 실행 시각: `2026-03-15T17:54:56.988899+09:00`

## 환경
- Python: `C:\Users\HP\AppData\Local\Programs\Python\Python313\python.exe`
- 의존성 설치 명령: `C:\Users\HP\AppData\Local\Programs\Python\Python313\python.exe -m pip install -U schemathesis pytest requests pyyaml`
- 의존성 설치 종료 코드: `0`
- Health check: `https://petstore.swagger.io/v2` 에서 상태 코드 `404` 를 확인했다.

## 생성된 파일
- `testcases.md`
- `test_api.py`
- `test_users_scenarios.py`
- `test_report.md`

## 아티팩트
- `D:/jhseo/project/swagger-api/.openapi-ai-agent/last-run/test_api.log`
- `D:/jhseo/project/swagger-api/.openapi-ai-agent/last-run/test_users_scenarios.log`
- `D:/jhseo/project/swagger-api/.openapi-ai-agent/last-run/run_summary.json`

## QA 관점 요약
- 시나리오 테스트 결과: `9개 통과 / 소요 시간 10.72s`
- 동적 스키마 테스트 결과: `20개 실패 / 소요 시간 32.59s`
- 해석: 대표 사용자 시나리오 기준으로는 기본 동작이 확인됐다.
- 해석: 동적 스키마 검사는 프로토콜/명세 적합성 이슈까지 포함하므로, 실사용 시나리오 실패와 동일하게 취급하면 안 된다.

## 테스트 실행 요약
### `test_api.py`
- 실행 명령: `C:\Users\HP\AppData\Local\Programs\Python\Python313\python.exe -X utf8 -m pytest test_api.py -q --tb=short`
- 종료 코드: `1`
- 요약: 20개 실패 / 소요 시간 32.59s
- 실패 근거:
  - + Exception Group Traceback (most recent call last):
  - |     raise FailureGroup(_failures, message) from None
  - | schemathesis.core.failures.FailureGroup: Schemathesis found 1 distinct failure
  - |     TRACE returned 405 without required `Allow` header
  - | TRACE returned 405 without required `Allow` header
- 추정: 동적 스키마 검사 중 HTTP 메서드 호환성 문제가 발견됐다. 실사용 시나리오 실패와는 분리해서 해석해야 한다.
- 전체 로그: `D:/jhseo/project/swagger-api/.openapi-ai-agent/last-run/test_api.log`

### `test_users_scenarios.py`
- 실행 명령: `C:\Users\HP\AppData\Local\Programs\Python\Python313\python.exe -X utf8 -m pytest test_users_scenarios.py -q --tb=short`
- 종료 코드: `0`
- 요약: 9개 통과 / 소요 시간 10.72s
- 전체 로그: `D:/jhseo/project/swagger-api/.openapi-ai-agent/last-run/test_users_scenarios.log`

## 해석 가이드
- 실패 근거는 명령 출력, 종료 코드, assertion 실패, 스키마 검증 실패에서 직접 추출했다.
- 추정은 빠른 분류를 돕기 위한 보조 진단이며, 최종 원인 판정은 아니다.
