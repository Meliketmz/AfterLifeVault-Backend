from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from access_code import router as access_code_router
from email_verification import router as email_verification_router
from vault import router as vault_router

app = FastAPI(title="Hello FastAPI")
app.include_router(access_code_router)
app.include_router(email_verification_router)
app.include_router(vault_router)


@app.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def not_found_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "İstenen kaynak bulunamadı."},
    )


@app.exception_handler(status.HTTP_403_FORBIDDEN)
async def forbidden_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": "Bu kaynağa erişim izniniz yok."},
    )


@app.get("/api/hello")
async def hello_api() -> dict[str, str]:
    return {"message": "Hello from FastAPI!"}
