"""MOA 서버 (FastAPI).

실행 (저장소 맨 위 폴더에서, CGI 환경):
    CGI\\Scripts\\python.exe -m uvicorn backend.main:app --port 8000

켜지면 AnyDoor 합성 모델을 뒤에서 미리 불러오고 예열한다 (그동안도 서버는 응답, 들어온 합성은 예열 뒤 처리).
합성을 안 쓰는 작업이라 예열을 끄려면: set MOA_WARMUP=0 후 실행.

주소와 주고받는 값은 팀 API 명세(docs/api.md)를 따른다. 모든 주소는 /api로 시작한다.
기능별로 routers/ 아래 파일을 하나씩 만들어 여기서 붙인다. 누가 어느 칸을 채우는지는 backend/README.md 참고.
"""
import os

from fastapi import FastAPI

from backend.errors import register_error_handlers
from backend.routers import compose, extract, files, images

app = FastAPI(title="MOA API")
register_error_handlers(app)  # 오류를 명세 형식 { error: { code, message } }으로


@app.get("/api/health")
def health():
    """서버가 켜져 있는지 확인용."""
    return {"status": "ok"}


# 기능별 주소
app.include_router(images.router)    # 명세 3-1 사진 올리기
app.include_router(files.router)     # 명세 7장 파일 보기
app.include_router(extract.router)   # 명세 4-1 상의 추출
app.include_router(compose.router)   # 명세 5-1~5-3 합성


@app.on_event("startup")
def _warmup_compose():
    if os.environ.get("MOA_WARMUP", "1") != "0":
        compose.start_warmup()


def _openapi_with_spec_errors():
    """/docs 화면의 오류 설명을 실제 동작(400 + 명세 형식)에 맞춘다.
    FastAPI는 기본으로 422와 {"detail": ...} 형식을 보여 주지만, 이 서버는 errors.py에서 400 + { error: { code, message } }로 바꿔 돌려준다."""
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    from backend.errors import ErrorResponse

    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    schema.setdefault("components", {}).setdefault("schemas", {})["ErrorResponse"] = ErrorResponse.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )
    for name, sub in ErrorResponse.model_json_schema(ref_template="#/components/schemas/{model}").get("$defs", {}).items():
        schema["components"]["schemas"][name] = sub
    schema["components"]["schemas"]["ErrorResponse"].pop("$defs", None)
    err = {"description": "실패 (명세 0장 오류 형식)", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}}
    for ops in schema.get("paths", {}).values():
        for op in ops.values():
            responses = op.get("responses", {})
            responses.pop("422", None)
            responses.setdefault("400", err)
    for unused in ("HTTPValidationError", "ValidationError"):
        schema["components"]["schemas"].pop(unused, None)
    app.openapi_schema = schema
    return schema


app.openapi = _openapi_with_spec_errors
