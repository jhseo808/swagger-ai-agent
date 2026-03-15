# Swagger/OpenAPI QA 자동화

Swagger URL과 OpenAPI `yaml/json` 파일만으로 테스트케이스 작성, API 검증, 시나리오 테스트, 결과 리포트 생성을 자동화하는 스킬 기반 QA 도구입니다.

## 왜 만들었는가

개발팀에서 Swagger URL과 명세 파일만 전달해 주는 경우가 많았고, QA는 그 문서를 기준으로 직접 Swagger UI에 들어가 엔드포인트를 하나씩 호출해야 했습니다.

이 과정에서 반복적으로 발생하던 문제는 다음과 같았습니다.

- 테스트케이스를 사람이 직접 정리해야 함
- 정상/예외 케이스를 수동으로 확인해야 함
- 응답 코드, 필수 파라미터, 인증 조건, 응답 스키마를 문서와 직접 비교해야 함
- 테스트 후 결과를 다시 보고서 형태로 정리해야 함

이 스킬은 위 과정을 줄이기 위해 만들었습니다.  
목표는 단순히 요청을 자동으로 보내는 것이 아니라, OpenAPI 명세를 기반으로 테스트 문서화, 검증, 실행, 결과 정리까지 한 번에 처리하는 것입니다.

## 무엇을 하는가

이 스킬은 아래 작업을 자동으로 수행합니다.

- Swagger URL 또는 OpenAPI 명세 파일 읽기
- OpenAPI 스펙 분석
- 테스트케이스 문서 생성
- `Schemathesis` 기반 동적 검증 테스트 생성
- `pytest + requests` 기반 시나리오 테스트 생성
- 테스트 실행 로그 저장
- Markdown 형식의 결과 리포트 생성

## 입력값

최소 입력값은 아래 두 가지입니다.

- Swagger/OpenAPI URL
- OpenAPI `yaml` 또는 `json` 파일 경로

예시:

- Swagger URL: `https://petstore.swagger.io/v2/swagger.json`
- 명세 파일 경로: `D:\jhseo\project\swagger-api\swagger\swagger.yaml`

## 실행 흐름

1. Swagger URL 또는 명세 파일을 입력받습니다.
2. OpenAPI 스펙을 파싱해 엔드포인트, 파라미터, 응답 구조, 인증 조건을 분석합니다.
3. 테스트케이스 문서 `testcases.md`를 생성합니다.
4. 동적 검증용 `test_api.py`를 생성합니다.
5. 시나리오 테스트용 `test_users_scenarios.py`를 생성합니다.
6. 테스트를 실행하고 로그를 저장합니다.
7. 실행 결과를 `test_report.md`로 정리합니다.

## 생성 결과물

- `testcases.md`: 명세 기반 테스트케이스 문서
- `test_api.py`: Schemathesis 기반 동적 검증 테스트
- `test_users_scenarios.py`: 주요 흐름 검증용 시나리오 테스트
- `test_report.md`: 테스트 결과 요약 리포트
- `.openapi-ai-agent/last-run/`: 실행 로그 및 요약 아티팩트

## 사용 방법

이 프로젝트는 로컬 서버를 띄워 테스트하는 방식이 아니라, 전달받은 Swagger/OpenAPI URL과 명세 파일만으로 테스트를 수행하는 방식입니다.

### 1. 환경 준비

필요한 Python 패키지는 아래와 같습니다.

- `schemathesis`
- `pytest`
- `requests`
- `pyyaml`

필요 시 아래 명령으로 설치할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -U schemathesis pytest requests pyyaml
```

### 2. PowerShell 스크립트로 실행

```powershell
.\.claude\skills\openapi-ai-agent\scripts\run_openapi_workflow.ps1 `
  -SwaggerUrl "https://petstore.swagger.io/v2/swagger.json" `
  -SpecSource "D:\jhseo\project\swagger-api\swagger\swagger.yaml" `
  -Workspace "."
```

### 3. Python 스크립트로 직접 실행

```powershell
.\.venv\Scripts\python.exe .\.claude\skills\openapi-ai-agent\scripts\run_openapi_workflow.py `
  --swagger-url "https://petstore.swagger.io/v2/swagger.json" `
  --spec-source "D:\jhseo\project\swagger-api\swagger\swagger.yaml" `
  --workspace "."
```

## 실행 후 확인할 파일

실행이 끝나면 아래 파일을 확인하면 됩니다.

- `testcases.md`
- `test_api.py`
- `test_users_scenarios.py`
- `test_report.md`
- `.openapi-ai-agent/last-run/`

## 현재 폴더 구조

```text
.
|-- .claude/
|   `-- skills/openapi-ai-agent/
|-- .openapi-ai-agent/
|-- swagger/
|   |-- swagger.yaml
|   |-- swagger_.yaml
|   |-- downloaded_openapi.json
|   `-- discovered_openapi.json
|-- testcases.md
|-- test_api.py
|-- test_users_scenarios.py
|-- test_report.md
|-- package.json
`-- README.md
```

## 참고

- 이 도구는 명세 기반 검증을 수행하므로, 테스트 결과는 환경 문제보다 명세와 실제 구현의 차이를 드러내는 데 더 의미가 있습니다.
- 현재 리포트 인코딩과 결과 표현 방식은 추가 개선 여지가 있습니다.
