---
name: openapi-ai-agent
description: Swagger UI 주소 또는 OpenAPI 명세를 자동으로 분석해서 API 테스트를 끝까지 수행하는 스킬이다. swagger URL, swagger ui page, swagger yaml/json, openapi spec file, base URL만 받아도 spec 탐색, 의존성 설치, 테스트케이스 생성, Schemathesis 테스트 코드 생성, pytest 시나리오 생성, 테스트 실행, 실행 로그 저장, markdown 리포트 작성까지 자동 처리할 때 사용한다. "테스트 진행해줘", "swagger 테스트해줘", "swagger 주소만 줄게", "yaml 받아서 자동으로 테스트해줘", "spec 기반으로 테스트 코드와 리포트까지 만들어줘" 같은 요청에서 트리거한다.
---

# OpenAPI AI Agent

사용자가 명시적으로 계획만 원하지 않는 한, 분석에서 멈추지 말고 전체 흐름을 자동으로 끝까지 수행한다.

재현성과 안정성을 위해 번들된 러너 스크립트를 우선 사용한다.

- PowerShell 진입점: `./.claude/skills/openapi-ai-agent/scripts/run_openapi_workflow.ps1`
- Python 구현체: `./.claude/skills/openapi-ai-agent/scripts/run_openapi_workflow.py`

Windows에서는 PowerShell 진입점을 먼저 사용한다. 이 스크립트는 사용 가능한 Python 인터프리터를 찾은 뒤 Python 워크플로우를 실행한다.

## 최소 입력 계약

가능하면 아래 입력만으로 처리한다.

- `swagger_url`: Swagger UI 페이지 주소 또는 raw OpenAPI 문서 주소
- `base_url`: 실제 테스트 대상 서버 주소. 없으면 명세의 `servers` 값을 우선 사용한다.
- `spec_source`: 이미 알고 있는 로컬 yaml/json 경로 또는 원격 yaml/json URL

사용자가 Swagger UI 주소만 줬다면, 먼저 명세를 자동으로 찾아낸다.

사용자에게 패키지 설치, 파일 생성, 테스트 전략 설명을 요구하지 않는다.

## 기본 실행 순서

1. 입력을 정규화한다.
2. 환경을 자동으로 준비한다.
3. OpenAPI 명세를 자동 발견하거나 다운로드해서 워크스페이스에 저장한다.
4. 명세를 파싱해서 엔드포인트, 파라미터, 요청 본문, 인증 요구사항, 스키마를 추출한다.
5. 대상 서버에 가벼운 health check를 수행한다.
6. 사람이 읽을 수 있는 테스트케이스 문서를 생성한다.
7. Schemathesis 기반 동적 테스트를 생성한다.
8. 문서화된 핵심 흐름 중심의 pytest 시나리오를 생성한다.
9. 테스트를 실행한다.
10. 실행 로그와 요약 artifact를 저장한다.
11. 증거 중심의 markdown 리포트를 생성한다.

환경이 허용하는 한, 한 번의 실행으로 전체 흐름을 끝낸다.

실행 가능한 환경이면 아래 명령을 우선 사용한다.

```powershell
./.claude/skills/openapi-ai-agent/scripts/run_openapi_workflow.ps1 -SwaggerUrl "<swagger_url>" -BaseUrl "<base_url>" -Workspace "."
```

또는

```powershell
./.claude/skills/openapi-ai-agent/scripts/run_openapi_workflow.ps1 -SpecSource "<spec_source>" -BaseUrl "<base_url>" -Workspace "."
```

## 입력 정규화 규칙

먼저 아래 런타임 변수를 결정한다.

- `BASE_URL`: 실제 테스트에 사용할 API 서버 주소
- `SPEC_PATH`: 워크스페이스 안에 저장된 OpenAPI 문서 경로
- `SPEC_ORIGIN`: 원래 명세를 가져온 위치

명세는 가능하면 `swagger/swagger.yaml`, `swagger/openapi.yaml`, `swagger/discovered_openapi.json`처럼 예측 가능한 위치에 저장한다.

원격 소스라면 생성 전에 워크스페이스로 다운로드한다.

사용자가 Swagger UI 페이지를 줬다면 아래 순서로 명세를 찾는다.

- `swagger-ui-init.js`를 읽는다.
- 직접 연결된 spec URL이 있으면 그 URL을 사용한다.
- Swagger UI 안에 `swaggerDoc`이 inline으로 포함되어 있으면 추출해서 사용한다.

사용자가 준 `base_url`과 명세의 `servers`가 다르면, 실제 테스트에는 사용자 입력을 우선 사용하고 리포트에 차이를 남긴다.

## 환경 준비 규칙

가능하면 가상환경을 사용한다.

필요한 의존성은 자동 설치 또는 업그레이드한다. 가능하면 bare `pip` 대신 `python -m pip`를 사용한다.

번들된 러너는 생성과 실행 전에 자동으로 의존성 설치를 시도한다.

최소 패키지:

- `schemathesis`
- `pytest`
- `requests`
- `pyyaml`

생성 테스트나 리포트 흐름에 다른 패키지가 분명히 필요하면 추가 설치한다.

설치에 실패하면 실패한 명령과 원인을 최종 응답 또는 리포트에 남긴다.

## 생성해야 하는 결과물

특별한 규칙이 없는 한, 아래 파일을 프로젝트 루트에 생성한다.

- `testcases.md`
- `test_api.py`
- `test_users_scenarios.py`
- `test_report.md`

생성되는 markdown 산출물은 항상 한국어로 작성한다.

- `testcases.md`와 `test_report.md`의 제목, 섹션명, 설명, 요약 문장, 추론 문장은 모두 한국어로 작성한다.
- 명세 안의 원문 `summary`나 설명이 영어라면 필요 시 원문으로 남길 수 있지만, 주변 설명 문장과 해석은 한국어로 유지한다.
- 실패 원인을 요약할 때는 `FAILED ...` 같은 잘린 한 줄 요약보다 실제 실패 블록의 핵심 메시지를 우선 기록한다.

실행 artifact는 아래 경로에 저장한다.

- `.openapi-ai-agent/last-run/`

이미 같은 이름의 파일이 있다면, 가능하면 조심스럽게 갱신한다. 사용자의 수동 수정 내용을 불필요하게 덮어쓰지 않는다.

## `testcases.md` 작성 규칙

명세에서 파생된 테스트 항목을 사람이 읽기 쉬운 markdown으로 정리한다.

중요한 엔드포인트와 메서드마다 최소한 아래 항목을 포함한다.

- 정상 성공 시나리오
- 필수 파라미터 또는 필수 바디 검증
- 문서화된 에러 응답
- 리소스 미존재 시 동작
- 인증이 정의된 경우 인증 실패 시나리오

명세가 보장하지 않는 강한 단정은 만들지 않는다. 추론이 섞인 항목은 반드시 추론임을 표시한다.

## `test_api.py` 작성 규칙

광범위한 동적 검증은 Schemathesis를 사용한다.

테스트 파일은 다음을 만족해야 한다.

- `SPEC_PATH`에서 명세를 읽는다.
- `BASE_URL`로 실제 API를 호출한다.
- 문서화된 응답 형식과 상태 코드를 검증한다.
- 명세가 명확히 보장하지 않는 정책은 강한 assertion으로 넣지 않는다.

하드코딩된 보안 헤더 규칙보다 스키마 기반 검증을 우선한다.

## `test_users_scenarios.py` 작성 규칙

Schemathesis가 표현하기 어려운 핵심 회귀 시나리오는 별도의 pytest 시나리오로 생성한다.

우선순위:

- 대표적인 happy path
- 필수값 검증
- 포맷 검증
- not found 동작
- 인증이 정의된 경우 인증 실패

프로젝트에서 다른 HTTP 클라이언트를 강하게 쓰지 않으면 `requests`를 사용한다.

테스트는 재실행 가능해야 한다. 고정 이메일, 고정 사용자명, 고정 ID로 인해 반복 실행이 깨지지 않도록 주의한다.

일반적인 HTTP 상식을 테스트로 단정하지 말고, 문서화된 동작을 우선 검증한다.

## 테스트 실행 규칙

테스트 파일을 생성한 뒤 자동으로 실행한다.

기본 실행 대상:

- `pytest test_api.py`
- `pytest test_users_scenarios.py`

프로젝트에 더 적절한 고립 실행 방식이 있으면 그 방식을 사용한다.

한 테스트 파일이 수집 실패나 런타임 오류로 중단되더라도, 가능한 다른 테스트 파일은 계속 실행하고 결과를 남긴다.

## `test_report.md` 작성 규칙

최종 리포트에는 최소한 아래 내용을 포함한다.

- 테스트한 `BASE_URL`
- 사용한 `SPEC_PATH`
- `SPEC_ORIGIN`
- 명세 확보 방식
- 실행 시각
- 사용한 Python 경로
- 의존성 설치 명령과 종료 코드
- 생성된 파일 목록
- 저장된 로그 파일 경로
- pytest 요약
- 중요한 실패와 근거
- 구현과 명세의 불일치
- 추정 원인과 후속 조치

실패 근거는 가능한 한 잘리지 않은 원문 메시지로 남긴다.

- `FAILED test_xxx ...`처럼 말줄임표가 들어간 요약 줄만 복사하지 않는다.
- assertion 메시지, schema validation 메시지, 재현용 요청, 핵심 예외 메시지처럼 원인을 직접 보여주는 줄을 우선 사용한다.

사실과 추론을 구분한다.

사실:

- 명령 실행 결과
- 종료 코드
- assertion 실패
- schema validation 실패
- 저장된 로그 내용

추론:

- 가능한 근본 원인
- 구현 버그 가능성
- 우선 확인할 수정 포인트

## 운영 원칙

- 사용자 설정 요청보다 자동화를 우선한다.
- 추측 전에 로컬 프로젝트 구조를 먼저 확인한다.
- 같은 산출물을 여러 이름으로 중복 생성하지 않는다.
- 큰 테스트 묶음보다 신뢰할 수 있는 테스트를 우선한다.
- 채팅 응답을 길게 늘이는 것보다 artifact와 리포트를 충실하게 남긴다.
- 명세, 실제 응답, 기존 프로젝트 로직이 뒷받침하지 않으면 버그라고 단정하지 않는다.
- 사용자가 주지 않은 `localhost`, `/api/v1`, 파일 경로, 자격 증명을 임의로 고정하지 않는다.

## 해석 예시

사용자가 이렇게 말하면:

`swagger 주소만 줄게. 테스트 진행해줘`

아래처럼 해석한다.

- Swagger UI 또는 raw spec에서 명세를 자동 확보한다.
- 필요하면 명세의 `servers`에서 `BASE_URL`을 유도한다.
- 의존성을 자동 설치한다.
- health check를 수행한다.
- `testcases.md`를 생성한다.
- `test_api.py`를 생성한다.
- `test_users_scenarios.py`를 생성한다.
- 테스트를 실행한다.
- 로그를 `.openapi-ai-agent/last-run/`에 저장한다.
- `test_report.md`를 생성한다.

접근 권한 부족, 네트워크 제약, 필수 입력 자체의 부재 같은 실제 장애가 없는 한, 설명만 하고 멈추지 않는다.
