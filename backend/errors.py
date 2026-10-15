"""오류 응답을 명세 형식으로 맞춘다.

명세 0장: { "error": { "code": "INVALID_IMAGE", "message": "이미지를 읽을 수 없습니다." } }
화면은 message를 그대로 안내 문구로 띄운다.
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """/docs 화면에 보여 줄 오류 형식"""
    error: ErrorDetail


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


def _body(code, message):
    return {"error": {"code": code, "message": message}}


def register_error_handlers(app: FastAPI):
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content=_body(exc.code, exc.message))

    # 없는 주소 등 FastAPI가 직접 내는 오류도 명세 형식으로
    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return JSONResponse(status_code=404, content=_body("NOT_FOUND", "찾을 수 없습니다."))
        if exc.status_code == 405:
            return JSONResponse(status_code=405, content=_body("METHOD_NOT_ALLOWED", "허용되지 않는 요청 방식입니다."))
        return JSONResponse(status_code=exc.status_code, content=_body("HTTP_ERROR", str(exc.detail)))

    # 필수 값이 빠졌거나 형식이 틀린 요청 (FastAPI 기본 형식 대신 명세 형식으로)
    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        fields = ", ".join(str(e["loc"][-1]) for e in exc.errors())
        return JSONResponse(status_code=400, content=_body("INVALID_REQUEST", f"요청 값이 올바르지 않습니다: {fields}"))
