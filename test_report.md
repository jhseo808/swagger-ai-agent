# API 테스트 리포트

## 실행 정보
- 테스트 대상 Base URL: `https://petstore.swagger.io/v2`
- 명세 파일 경로: `D:/jhseo/project/swagger-api/swagger/swagger.yaml`
- 명세 원본 위치: `D:\jhseo\project\swagger-api\swagger\swagger.yaml`
- 명세 확보 방식: `explicit-file`
- 실행 시각: `2026-03-15T18:10:41.871006+09:00`

## 환경
- Python: `D:\jhseo\project\swagger-api\.venv\Scripts\python.exe`
- 의존성 설치 명령: `D:\jhseo\project\swagger-api\.venv\Scripts\python.exe -m pip install -U schemathesis pytest requests pyyaml`
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

## QA 요약
- 시나리오 테스트 결과: `9개 통과 / 소요 시간 10.31s`
- 동적 스키마 테스트 결과: `20개 실패 / 소요 시간 33.06s`
- 해석: 주요 사용자 시나리오 기준의 기본 동작은 확인됐다.
- 해석: 동적 스키마 검증은 프로토콜 및 명세 적합성까지 포함하므로 시나리오 테스트와 분리해서 봐야 한다.

## 테스트 실행 요약
### `test_api.py`
- 실행 명령: `D:\jhseo\project\swagger-api\.venv\Scripts\python.exe -X utf8 -m pytest test_api.py -q --tb=short`
- 종료 코드: `1`
- 요약: `20개 실패 / 소요 시간 33.06s`
- 실패 근거:
  - `TRACE returned 405 without required Allow header`
  - `GET /store/inventory` 는 인증 없이 `200 OK` 를 반환했다.
  - `GET /user/login` 응답 본문이 명세의 `string` 타입과 일치하지 않았다.
  - `GET /user/login` 의 `X-Expires-After` 헤더가 `date-time` 형식과 일치하지 않았다.
  - 일부 요청은 필수 입력 또는 인증 헤더 누락을 거부하지 않았다.
- 추정: 동적 스키마 검증 중 HTTP 메서드 처리 규약 위반과 명세 불일치가 함께 발견됐다.
- 전체 로그: `D:/jhseo/project/swagger-api/.openapi-ai-agent/last-run/test_api.log`

### `test_users_scenarios.py`
- 실행 명령: `D:\jhseo\project\swagger-api\.venv\Scripts\python.exe -X utf8 -m pytest test_users_scenarios.py -q --tb=short`
- 종료 코드: `0`
- 요약: `9개 통과 / 소요 시간 10.31s`
- 전체 로그: `D:/jhseo/project/swagger-api/.openapi-ai-agent/last-run/test_users_scenarios.log`

## 정상 동작 검증 항목
- `test_api.py` 에서는 실제 통과한 케이스가 없었다. 결과는 `20 failed` 였다.
- `test_api.py` 가 동적으로 검증한 operation 목록은 다음과 같다.
  - `POST /pet/{petId}/uploadImage`
  - `POST /pet`
  - `PUT /pet`
  - `GET /pet/findByStatus`
  - `GET /pet/findByTags`
  - `GET /pet/{petId}`
  - `POST /pet/{petId}`
  - `DELETE /pet/{petId}`
  - `GET /store/inventory`
  - `POST /store/order`
  - `GET /store/order/{orderId}`
  - `DELETE /store/order/{orderId}`
  - `POST /user/createWithList`
  - `GET /user/{username}`
  - `PUT /user/{username}`
  - `DELETE /user/{username}`
  - `GET /user/login`
  - `GET /user/logout`
  - `POST /user/createWithArray`
  - `POST /user`
- 정상 동작 기준으로 실제 통과한 테스트는 `test_users_scenarios.py` 의 9개였다.
  - `GET /pet/findByStatus` happy path
  - `GET /store/inventory` happy path
  - `GET /user/login` happy path
  - `GET /pet/{petId}` resource lookup
  - `GET /pet/{petId}` not found
  - `GET /store/order/{orderId}` resource lookup
  - `GET /store/order/{orderId}` not found
  - `GET /user/{username}` resource lookup
  - `GET /user/{username}` not found

## 해석 가이드
- 실패 근거는 명령 출력, 종료 코드, assertion 실패, 스키마 검증 실패에서 직접 추출했다.
- 추정은 빠른 분류를 위한 보조 진단이며 최종 원인 확정은 아니다.
