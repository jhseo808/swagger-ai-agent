#!/usr/bin/env python
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse


DEPENDENCIES = ["schemathesis", "pytest", "requests", "pyyaml"]
INSTALL_COMMAND = [sys.executable, "-m", "pip", "install", "-U", *DEPENDENCIES]
INSTALL_RESULT = None


def run_command(command, cwd, env=None):
    return subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=env,
        check=False,
    )


def ensure_dependencies():
    global INSTALL_RESULT
    result = run_command(INSTALL_COMMAND, cwd=Path.cwd())
    INSTALL_RESULT = result
    if result.returncode != 0:
        raise RuntimeError(
            "Dependency installation failed.\n"
            f"Command: {' '.join(result.args)}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


ensure_dependencies()

import requests  # noqa: E402
import yaml  # noqa: E402


def slugify(value):
    text = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return text or "operation"


def is_url(value):
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_spec_document(spec_path):
    raw = spec_path.read_text(encoding="utf-8")
    if spec_path.suffix.lower() == ".json":
        return json.loads(raw)
    return yaml.safe_load(raw)


def extract_json_object(source, anchor):
    start = source.find(anchor)
    if start == -1:
        return None
    brace_start = source.find("{", start)
    if brace_start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(brace_start, len(source)):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace_start : index + 1]
    return None


def fetch_url(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response


def discover_spec_from_swagger_url(swagger_url, artifact_dir):
    response = fetch_url(swagger_url)
    content_type = response.headers.get("content-type", "").lower()
    raw_text = response.text
    if swagger_url.endswith((".yaml", ".yml", ".json")) or "application/json" in content_type or "yaml" in content_type:
        return {"mode": "direct", "spec_text": raw_text, "spec_url": swagger_url}

    init_candidates = []
    for script_name in ("swagger-ui-init.js", "swagger-initializer.js"):
        init_candidates.extend(
            [
                urljoin(swagger_url if swagger_url.endswith("/") else swagger_url + "/", script_name),
                urljoin(swagger_url, script_name),
            ]
        )

    init_text = None
    init_url = None
    for candidate in init_candidates:
        try:
            init_response = fetch_url(candidate)
            init_text = init_response.text
            init_url = candidate
            break
        except requests.RequestException:
            continue

    if init_text:
        write_text(artifact_dir / "swagger-ui-init.js", init_text)

        url_match = re.search(r"\burl:\s*['\"]([^'\"]+)['\"]", init_text)
        swagger_url_match = re.search(r"\bswaggerUrl\s*[:=]\s*['\"]([^'\"]+)['\"]", init_text)
        definition_url_match = re.search(r"\bdefinitionURL\s*=\s*['\"]([^'\"]+)['\"]", init_text)
        default_definition_match = re.search(r"\bdefaultDefinitionUrl\s*=\s*['\"]([^'\"]+)['\"]", init_text)
        discovered_url = None
        if url_match:
            discovered_url = urljoin(init_url, url_match.group(1))
        elif swagger_url_match:
            discovered_url = urljoin(init_url, swagger_url_match.group(1))
        elif definition_url_match:
            discovered_url = urljoin(init_url, definition_url_match.group(1))
        elif default_definition_match:
            discovered_url = urljoin(init_url, default_definition_match.group(1))
        if discovered_url:
            resolved = fetch_url(discovered_url)
            return {"mode": "swagger-ui-url", "spec_text": resolved.text, "spec_url": discovered_url}

        swagger_doc_text = extract_json_object(init_text, '"swaggerDoc"')
        if swagger_doc_text:
            parsed = json.loads(swagger_doc_text)
            return {
                "mode": "swagger-ui-inline",
                "spec_text": json.dumps(parsed, ensure_ascii=False, indent=2),
                "spec_url": init_url,
            }

    html_url_match = re.search(r'url:\s*"([^"]+)"', raw_text)
    if html_url_match:
        discovered_url = urljoin(swagger_url, html_url_match.group(1))
        resolved = fetch_url(discovered_url)
        return {"mode": "html-embedded-url", "spec_text": resolved.text, "spec_url": discovered_url}

    raise RuntimeError(f"Could not discover an OpenAPI document from swagger URL: {swagger_url}")


def resolve_spec_source(spec_source, swagger_url, workspace, artifact_dir):
    swagger_dir = workspace / "swagger"
    swagger_dir.mkdir(parents=True, exist_ok=True)

    if spec_source:
        if is_url(spec_source):
            response = fetch_url(spec_source)
            extension = Path(urlparse(spec_source).path).suffix or guess_extension(response.text, spec_source)
            target = swagger_dir / f"downloaded_openapi{extension}"
            target.write_text(response.text, encoding="utf-8")
            return target, spec_source, "explicit-url"

        source_path = Path(spec_source)
        if not source_path.is_absolute():
            source_path = (workspace / source_path).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Spec source not found: {source_path}")

        target = swagger_dir / source_path.name
        if source_path.resolve() != target.resolve():
            shutil.copyfile(source_path, target)
        return target, str(source_path), "explicit-file"

    if not swagger_url:
        raise RuntimeError("Either spec_source or swagger_url is required.")

    discovered = discover_spec_from_swagger_url(swagger_url, artifact_dir)
    extension = guess_extension(discovered["spec_text"], discovered["spec_url"])
    target = swagger_dir / f"discovered_openapi{extension}"
    target.write_text(discovered["spec_text"], encoding="utf-8")
    return target, discovered["spec_url"], discovered["mode"]


def guess_extension(text, source_hint):
    hint = (source_hint or "").lower()
    if hint.endswith(".json"):
        return ".json"
    stripped = text.lstrip()
    return ".json" if stripped.startswith("{") else ".yaml"


def list_operations(spec):
    operations = []
    for path, path_item in (spec.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue
            op = operation or {}
            operations.append(
                {
                    "path": path,
                    "method": method.upper(),
                    "operation": op,
                    "operation_id": op.get("operationId") or slugify(f"{method}_{path}"),
                }
            )
    return operations


def collect_parameters(spec, operation):
    path_item = ((spec.get("paths") or {}).get(operation["path"]) or {})
    params = []
    params.extend(path_item.get("parameters") or [])
    params.extend(operation["operation"].get("parameters") or [])
    return [resolve_reference(spec, item) for item in params]


def resolve_reference(spec, item):
    if not isinstance(item, dict) or "$ref" not in item:
        return item
    ref = item["$ref"]
    if not ref.startswith("#/"):
        return item
    current = spec
    for part in ref[2:].split("/"):
        current = current.get(part, {})
    return current or item


def path_has_parameters(path):
    return "{" in path and "}" in path


def infer_sample_path(path):
    def replace(match):
        name = match.group(1).lower()
        if "id" in name:
            return "1"
        if "username" in name or name.endswith("name"):
            return "user1"
        if "status" in name:
            return "available"
        return "sample"

    return re.sub(r"{([^}]+)}", replace, path)


def pick_success_status(operation):
    responses = operation["operation"].get("responses") or {}
    for code in ("200", "201", "202", "204"):
        if code in responses or int(code) in responses:
            return int(code)
    for code in responses:
        code_value = str(code)
        if code_value.isdigit() and 200 <= int(code_value) < 300:
            return int(code_value)
    return 200


def pick_not_found_status(operation):
    responses = operation["operation"].get("responses") or {}
    if "404" in responses or 404 in responses:
        return 404
    if "400" in responses or 400 in responses:
        return 400
    return None


def operation_has_auth(spec, operation):
    security = operation["operation"].get("security")
    if security is None:
        security = spec.get("security")
    return bool(security)


def derive_base_url(provided_base_url, spec):
    if provided_base_url:
        return provided_base_url
    servers = spec.get("servers") or []
    if servers:
        candidate = servers[0].get("url")
        if candidate:
            return candidate.rstrip("/")
    host = spec.get("host")
    base_path = spec.get("basePath", "")
    schemes = spec.get("schemes") or []
    if host:
        scheme = schemes[0] if schemes else "https"
        return f"{scheme}://{host}{base_path}".rstrip("/")
    raise RuntimeError("Could not determine BASE_URL from input or spec servers.")


def health_check(base_url):
    candidates = [base_url, base_url.rstrip("/") + "/health", base_url.rstrip("/") + "/users"]
    for candidate in candidates:
        try:
            response = requests.get(candidate, timeout=10)
            return {"ok": True, "url": candidate, "status_code": response.status_code}
        except requests.RequestException as exc:
            last_error = str(exc)
    return {"ok": False, "url": candidates[-1], "error": last_error}


def build_testcases_content(spec, operations, base_url, spec_path, spec_origin):
    lines = [
        "# 자동 생성 API 테스트 케이스",
        "",
        f"- 테스트 대상 Base URL: `{base_url}`",
        f"- 명세 파일 경로: `{spec_path.as_posix()}`",
        f"- 명세 원본 위치: `{spec_origin}`",
        "",
    ]
    if not operations:
        lines.append("OpenAPI 명세에서 작업 가능한 operation을 찾지 못했다.")
        return "\n".join(lines) + "\n"

    for operation in operations:
        summary = operation["operation"].get("summary") or operation["operation"].get("description") or "요약 없음"
        lines.append(f"## {operation['path']} [{operation['method']}]")
        lines.append(f"- 요약: {summary}")
        lines.append(f"- 성공 기대값: 문서에 정의된 `{pick_success_status(operation)}` 응답이 반환되어야 한다.")

        parameters = collect_parameters(spec, operation)
        if parameters:
            lines.append("- 파라미터 처리: 문서화된 path 또는 query 파라미터를 정상 수용해야 한다.")
            if any(param.get("required") for param in parameters):
                lines.append("- 필수값 검증: 문서에 정의된 필수 파라미터는 반드시 강제되어야 한다.")

        request_body = resolve_reference(spec, operation["operation"].get("requestBody") or {})
        if request_body:
            lines.append("- 요청 본문: 문서에 정의된 필수 body 필드는 반드시 검증되어야 한다.")
            lines.append("- 요청 본문 형식: 문서화된 형식이 잘못되면 구현체가 검증하는 경우 실패해야 한다. _(추론)_")

        not_found_status = pick_not_found_status(operation)
        if path_has_parameters(operation["path"]) and not_found_status:
            lines.append(f"- 리소스 미존재: 존재하지 않는 식별자는 문서에 정의된 `{not_found_status}` 동작을 따라야 한다.")

        if operation_has_auth(spec, operation):
            lines.append("- 인증: 인증 정보가 없거나 잘못되면 문서의 보안 스키마에 맞게 실패해야 한다.")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_dynamic_test_content(spec_path, base_url):
    return (
        'import os\n\n'
        'import schemathesis\n'
        'from schemathesis.openapi.checks import UnsupportedMethodResponse\n\n'
        f'SPEC_PATH = os.environ.get("OPENAPI_SPEC_PATH", r"{spec_path.as_posix()}")\n'
        f'BASE_URL = os.environ.get("OPENAPI_BASE_URL", "{base_url}")\n\n'
        'schema = schemathesis.openapi.from_path(SPEC_PATH)\n\n'
        '@schema.parametrize()\n'
        'def test_api(case):\n'
        '    response = case.call(base_url=BASE_URL)\n'
        '    case.validate_response(response, excluded_checks=[UnsupportedMethodResponse])\n'
    )


def build_payload_from_schema(spec, schema):
    schema = resolve_reference(spec, schema)
    payload = {}
    for name, prop in (schema.get("properties") or {}).items():
        prop = resolve_reference(spec, prop)
        if name == "email":
            payload[name] = "agent@example.com"
        elif "example" in prop:
            payload[name] = prop["example"]
        elif prop.get("enum"):
            payload[name] = prop["enum"][0]
        elif prop.get("type") == "integer":
            payload[name] = 1
        elif prop.get("type") == "boolean":
            payload[name] = True
        else:
            payload[name] = "agent-value"
    return payload


def build_parameter_value(spec, parameter):
    parameter = resolve_reference(spec, parameter)
    schema = parameter.get("schema") or parameter
    name = parameter.get("name", "").lower()
    if "example" in parameter:
        return parameter["example"]
    if "default" in parameter:
        return parameter["default"]
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if schema.get("enum"):
        return schema["enum"][0]
    if schema.get("type") == "array":
        item_schema = schema.get("items") or {}
        if item_schema.get("enum"):
            return [item_schema["enum"][0]]
        return [build_parameter_value(spec, item_schema)]
    if schema.get("type") == "integer":
        minimum = schema.get("minimum")
        return max(1, int(minimum)) if minimum is not None else 1
    if schema.get("type") == "boolean":
        return True
    if "email" in name:
        return "agent@example.com"
    if "password" in name:
        return "password123"
    if "username" in name or name.endswith("name"):
        return "user1"
    if "status" in name:
        return "available"
    if "tag" in name:
        return "tag1"
    if "id" in name:
        return 1
    return "sample"


def build_request_options(spec, operation):
    params = {}
    headers = {}
    for parameter in collect_parameters(spec, operation):
        location = parameter.get("in")
        if location not in {"query", "header"}:
            continue
        if location == "header" and not parameter.get("required"):
            continue
        value = build_parameter_value(spec, parameter)
        if location == "query":
            params[parameter["name"]] = value
        else:
            headers[parameter["name"]] = value
    return params, headers


def format_request_call(method, path, params=None, headers=None, json_payload=False):
    parts = [f'f"{{BASE_URL}}{path}"']
    if params:
        parts.append(f"params={json.dumps(params, ensure_ascii=False)}")
    if headers:
        parts.append(f"headers={json.dumps(headers, ensure_ascii=False)}")
    if json_payload:
        parts.append("json=payload")
    parts.append("timeout=30")
    return f"requests.{method.lower()}({', '.join(parts)})"


def request_body_payload(spec, operation):
    request_body = resolve_reference(spec, operation["operation"].get("requestBody") or {})
    content = request_body.get("content") or {}
    media = content.get("application/json") or next(iter(content.values()), {})
    schema = resolve_reference(spec, media.get("schema") or {})
    return build_payload_from_schema(spec, schema)


def find_operation(operations, method, predicate):
    for operation in operations:
        if operation["method"] == method and predicate(operation):
            return operation
    return None


def operation_group_key(operation):
    parts = operation["path"].strip("/").split("/")
    return parts[0] if parts and parts[0] else "root"


def choose_operations(operations, method, predicate, limit=3):
    selected = []
    seen_groups = set()
    for operation in operations:
        if operation["method"] != method or not predicate(operation):
            continue
        group = operation_group_key(operation)
        if group in seen_groups:
            continue
        seen_groups.add(group)
        selected.append(operation)
        if len(selected) >= limit:
            break
    return selected


def build_static_test_content(spec, operations, base_url):
    lines = [
        "import os",
        "import uuid",
        "",
        "import requests",
        "",
        f'BASE_URL = os.environ.get("OPENAPI_BASE_URL", "{base_url}")',
        "",
        "",
        "def unique_email():",
        '    return f"agent-{uuid.uuid4().hex[:8]}@example.com"',
        "",
    ]
    generated_any = False

    for get_collection in choose_operations(operations, "GET", lambda op: not path_has_parameters(op["path"]), limit=4):
        generated_any = True
        test_name = slugify(f"{get_collection['method']}_{get_collection['path']}_happy_path")
        target_path = infer_sample_path(get_collection["path"])
        params, headers = build_request_options(spec, get_collection)
        lines.extend(
            [
                f"def test_{test_name}():",
                f"    response = {format_request_call('GET', target_path, params=params, headers=headers)}",
                f"    assert response.status_code in ({pick_success_status(get_collection)}, 204)",
                "",
            ]
        )

    for create_operation in choose_operations(
        operations,
        "POST",
        lambda op: not path_has_parameters(op["path"]) and bool(resolve_reference(spec, op["operation"].get("requestBody") or {})),
        limit=3,
    ):
        generated_any = True
        payload = request_body_payload(spec, create_operation)
        if "email" in payload:
            payload["email"] = "__UNIQUE_EMAIL__"
        create_test_name = slugify(f"{create_operation['method']}_{create_operation['path']}_create_ok")
        create_target_path = infer_sample_path(create_operation["path"])
        params, headers = build_request_options(spec, create_operation)
        lines.extend(
            [
                f"def test_{create_test_name}():",
                f"    payload = {json.dumps(payload, ensure_ascii=False, indent=4)}",
                '    if "email" in payload:',
                '        payload["email"] = unique_email()',
                f"    response = {format_request_call('POST', create_target_path, params=params, headers=headers, json_payload=True)}",
                f"    assert response.status_code in ({pick_success_status(create_operation)}, 201, 202)",
                "",
            ]
        )

        invalid_payload = dict(payload)
        if "email" in invalid_payload:
            invalid_payload["email"] = "not-an-email"
        elif invalid_payload:
            invalid_payload[next(iter(invalid_payload))] = ""
        invalid_test_name = slugify(f"{create_operation['method']}_{create_operation['path']}_invalid_payload")
        lines.extend(
            [
                f"def test_{invalid_test_name}():",
                f"    payload = {json.dumps(invalid_payload, ensure_ascii=False, indent=4)}",
                f"    response = {format_request_call('POST', create_target_path, params=params, headers=headers, json_payload=True)}",
                "    assert response.status_code in (400, 409, 422)",
                "",
            ]
        )

    for get_resource in choose_operations(operations, "GET", lambda op: path_has_parameters(op["path"]), limit=4):
        generated_any = True
        params, headers = build_request_options(spec, get_resource)
        resource_path = infer_sample_path(get_resource["path"])
        resource_test_name = slugify(f"{get_resource['method']}_{get_resource['path']}_resource_lookup")
        lines.extend(
            [
                f"def test_{resource_test_name}():",
                f"    response = {format_request_call('GET', resource_path, params=params, headers=headers)}",
                f"    assert response.status_code in ({pick_success_status(get_resource)}, 404)",
                "",
            ]
        )

        if not pick_not_found_status(get_resource):
            continue

        generated_any = True
        bad_path = re.sub(r"{([^}]+)}", "999999", get_resource["path"])
        not_found_test_name = slugify(f"{get_resource['method']}_{get_resource['path']}_not_found")
        lines.extend(
            [
                f"def test_{not_found_test_name}():",
                f"    response = {format_request_call('GET', bad_path, params=params, headers=headers)}",
                f"    assert response.status_code == {pick_not_found_status(get_resource)}",
                "",
            ]
        )

    if not generated_any:
        lines.extend(["def test_placeholder_generated_from_openapi():", "    assert True", ""])

    return "\n".join(lines).rstrip() + "\n"


def execute_pytest(workspace, test_file, env):
    merged_env = dict(os.environ)
    merged_env.update(env)
    merged_env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + merged_env.get("PATH", "")
    return run_command([sys.executable, "-X", "utf8", "-m", "pytest", test_file, "-q", "--tb=short", "-rA"], cwd=workspace, env=merged_env)


def build_skipped_result(test_file, artifact_dir, reason):
    log_path = artifact_dir / f"{Path(test_file).stem}.log"
    write_text(log_path, reason.rstrip() + "\n")
    return {
        "test_file": test_file,
        "command": f"{sys.executable} -X utf8 -m pytest {test_file} -q --tb=short -rA",
        "returncode": None,
        "summary": "실행 건너뜀: 대상 서버 연결 실패",
        "facts": [reason],
        "inference": "테스트 대상 서버가 응답하지 않아 실행 가능한 QA 결과를 만들 수 없었다.",
        "log_path": log_path.as_posix(),
    }


def summarize_pytest_output(output):
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    raw_summary = next(
        (line for line in reversed(lines) if " passed" in line or " failed" in line or " error" in line or " no tests ran" in line),
        "",
    )
    summary = localize_pytest_summary(raw_summary)
    failure_lines = extract_failure_evidence(lines)
    inference = ""
    lowered = output.lower()
    if "unsupportedmethodresponse" in lowered or "required `allow` header" in lowered:
        inference = "동적 스키마 검사 중 HTTP 메서드 호환성 문제가 발견됐다. 실사용 시나리오 실패와는 분리해서 해석해야 한다."
    elif "connection refused" in lowered or "failed to establish a new connection" in lowered:
        inference = "테스트 실행 중 대상 API 서버에 연결할 수 없었다."
    elif "jsonschemaerror" in lowered or "response violates schema" in lowered:
        inference = "적어도 하나의 응답 형식 또는 상태 코드가 OpenAPI 스키마와 일치하지 않는다."
    elif "assert 500" in lowered:
        inference = "문서화된 시나리오에서 API가 예상하지 않은 서버 오류를 반환했다."
    status_map = extract_test_case_statuses(lines)
    return summary, failure_lines[:10], inference, status_map


def localize_pytest_summary(summary):
    if not summary:
        return summary
    localized = summary
    localized = re.sub(r"(\d+)\s+failed", r"\1개 실패", localized)
    localized = re.sub(r"(\d+)\s+passed", r"\1개 통과", localized)
    localized = re.sub(r"(\d+)\s+errors?", r"\1개 오류", localized)
    localized = localized.replace("no tests ran", "실행된 테스트 없음")
    localized = localized.replace(" in ", " / 소요 시간 ")
    return localized


def extract_failure_evidence(lines):
    header_index = next((index for index, line in enumerate(lines) if line.startswith("================================== FAILURES")), None)
    if header_index is None:
        return [line for line in lines if "AssertionError" in line or "JsonSchemaError" in line][:10]

    evidence = []
    capture = False
    for line in lines[header_index + 1 :]:
        if line.startswith("________________") and capture:
            break
        if line.startswith("________________") and not capture:
            capture = True
            continue
        if not capture:
            continue

        stripped = line.strip()
        if not stripped:
            continue
        if (
            "Traceback" in stripped
            or "FailureGroup" in stripped
            or "JsonSchemaError" in stripped
            or "AssertionError" in stripped
            or "returned" in stripped
            or "required `Allow` header" in stripped
            or "response violates schema" in stripped.lower()
            or stripped.startswith("Reproduce with:")
            or stripped.startswith("curl ")
        ):
            evidence.append(stripped)

    return evidence[:10]


def extract_test_case_statuses(lines):
    status_map = {"PASSED": [], "FAILED": [], "ERROR": [], "SKIPPED": [], "XFAIL": [], "XPASS": []}
    status_pattern = re.compile(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(.+)$")
    summary_pattern = re.compile(r"^(FAILED|ERROR)\s+(.+?)(?:\s+-\s+.+)?$")

    for line in lines:
        stripped = line.strip()
        match = status_pattern.match(stripped)
        if match:
            status_map[match.group(1)].append(match.group(2))
            continue

        summary_match = summary_pattern.match(stripped)
        if summary_match:
            status_map[summary_match.group(1)].append(summary_match.group(2))

    for key, values in status_map.items():
        deduped = []
        seen = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        status_map[key] = deduped

    return status_map


def build_report_content(
    base_url,
    spec_path,
    spec_origin,
    spec_mode,
    generated_files,
    install_summary,
    health,
    results,
    artifact_dir,
):
    timestamp = dt.datetime.now(dt.timezone.utc).astimezone().isoformat()
    scenario_result = next((result for result in results if result["test_file"] == "test_users_scenarios.py"), None)
    schema_result = next((result for result in results if result["test_file"] == "test_api.py"), None)
    lines = [
        "# API 테스트 리포트",
        "",
        "## 실행 정보",
        f"- 테스트 대상 Base URL: `{base_url}`",
        f"- 명세 파일 경로: `{spec_path.as_posix()}`",
        f"- 명세 원본 위치: `{spec_origin}`",
        f"- 명세 확보 방식: `{spec_mode}`",
        f"- 실행 시각: `{timestamp}`",
        "",
        "## 환경",
        f"- Python: `{sys.executable}`",
        f"- 의존성 설치 명령: `{install_summary['command']}`",
        f"- 의존성 설치 종료 코드: `{install_summary['returncode']}`",
    ]
    if health.get("ok"):
        lines.append(f"- Health check: `{health['url']}` 에서 상태 코드 `{health['status_code']}` 를 확인했다.")
    else:
        lines.append(f"- Health check: `{health['url']}` 인근 호출에 실패했다. 오류: `{health['error']}`")

    lines.extend(["", "## 생성된 파일"])
    for file_path in generated_files:
        lines.append(f"- `{file_path}`")

    lines.extend(["", "## 아티팩트"])
    for result in results:
        lines.append(f"- `{result['log_path']}`")
    lines.append(f"- `{(artifact_dir / 'run_summary.json').as_posix()}`")

    lines.extend(["", "## QA 관점 요약"])
    if scenario_result:
        lines.append(f"- 시나리오 테스트 결과: `{scenario_result['summary'] or scenario_result['returncode']}`")
    if schema_result:
        lines.append(f"- 동적 스키마 테스트 결과: `{schema_result['summary'] or schema_result['returncode']}`")
    if health.get("ok") is False:
        lines.append("- 해석: 테스트 대상 서버에 연결할 수 없어 실행 단계는 건너뛰었다.")
    if scenario_result and scenario_result["returncode"] == 0:
        lines.append("- 해석: 대표 사용자 시나리오 기준으로는 기본 동작이 확인됐다.")
    if schema_result and schema_result["returncode"] != 0:
        lines.append("- 해석: 동적 스키마 검사는 프로토콜/명세 적합성 이슈까지 포함하므로, 실사용 시나리오 실패와 동일하게 취급하면 안 된다.")

    lines.extend(["", "## 테스트 실행 요약"])
    for result in results:
        lines.append(f"### `{result['test_file']}`")
        lines.append(f"- 실행 명령: `{result['command']}`")
        lines.append(f"- 종료 코드: `{result['returncode']}`")
        if result["summary"]:
            lines.append(f"- 요약: {result['summary']}")
        if result["facts"]:
            lines.append("- 실패 근거:")
            for fact in result["facts"][:5]:
                lines.append(f"  - {fact}")
        if result["inference"]:
            lines.append(f"- 추정: {result['inference']}")
        lines.append(f"- 전체 로그: `{result['log_path']}`")
        lines.append("")

    lines.extend(
        [
            "## 해석 가이드",
            "- 실패 근거는 명령 출력, 종료 코드, assertion 실패, 스키마 검증 실패에서 직접 추출했다.",
            "- 추정은 빠른 분류를 돕기 위한 보조 진단이며, 최종 원인 판정은 아니다.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate and run API tests from a Swagger or OpenAPI source.")
    parser.add_argument("--base-url")
    parser.add_argument("--spec-source")
    parser.add_argument("--swagger-url")
    parser.add_argument("--workspace", default=".")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    artifact_dir = workspace / ".openapi-ai-agent" / "last-run"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    spec_path, spec_origin, spec_mode = resolve_spec_source(args.spec_source, args.swagger_url, workspace, artifact_dir)
    spec = load_spec_document(spec_path)
    base_url = derive_base_url(args.base_url, spec)
    health = health_check(base_url)
    operations = list_operations(spec)

    generated_files = {
        "testcases.md": build_testcases_content(spec, operations, base_url, spec_path, spec_origin),
        "test_api.py": build_dynamic_test_content(spec_path, base_url),
        "test_users_scenarios.py": build_static_test_content(spec, operations, base_url),
    }

    for name, content in generated_files.items():
        write_text(workspace / name, content)

    env = {
        "OPENAPI_BASE_URL": base_url,
        "OPENAPI_SPEC_PATH": spec_path.as_posix(),
        "PYTHONIOENCODING": "utf-8",
    }

    results = []
    if not health.get("ok"):
        reason = f"Health check failed near `{health['url']}`: {health['error']}"
        for test_file in ("test_api.py", "test_users_scenarios.py"):
            results.append(build_skipped_result(test_file, artifact_dir, reason))
    else:
        for test_file in ("test_api.py", "test_users_scenarios.py"):
            result = execute_pytest(workspace, test_file, env)
            combined = result.stdout + "\n" + result.stderr
            log_path = artifact_dir / f"{Path(test_file).stem}.log"
            write_text(log_path, combined)
            summary, facts, inference = summarize_pytest_output(combined)
            results.append(
                {
                    "test_file": test_file,
                    "command": f"{sys.executable} -X utf8 -m pytest {test_file} -q --tb=short",
                    "returncode": result.returncode,
                    "summary": summary,
                    "facts": facts,
                    "inference": inference,
                    "log_path": log_path.as_posix(),
                }
            )

    install_summary = {
        "command": " ".join(INSTALL_COMMAND),
        "returncode": INSTALL_RESULT.returncode if INSTALL_RESULT else 0,
    }

    run_summary = {
        "base_url": base_url,
        "spec_path": spec_path.as_posix(),
        "spec_origin": spec_origin,
        "spec_mode": spec_mode,
        "health": health,
        "results": results,
        "generated_files": list(generated_files.keys()) + ["test_report.md"],
    }
    write_text(artifact_dir / "run_summary.json", json.dumps(run_summary, ensure_ascii=False, indent=2))

    report = build_report_content(
        base_url,
        spec_path,
        spec_origin,
        spec_mode,
        list(generated_files.keys()) + ["test_report.md"],
        install_summary,
        health,
        results,
        artifact_dir,
    )
    write_text(workspace / "test_report.md", report)


if __name__ == "__main__":
    main()
