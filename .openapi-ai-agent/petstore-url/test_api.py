import os

import schemathesis
from schemathesis.openapi.checks import UnsupportedMethodResponse

SPEC_PATH = os.environ.get("OPENAPI_SPEC_PATH", r"D:/jhseo/project/swagger-api/swagger/discovered_openapi.json")
BASE_URL = os.environ.get("OPENAPI_BASE_URL", "https://petstore.swagger.io/v2")

schema = schemathesis.openapi.from_path(SPEC_PATH)

@schema.parametrize()
def test_api(case):
    response = case.call(base_url=BASE_URL)
    case.validate_response(response, excluded_checks=[UnsupportedMethodResponse])
