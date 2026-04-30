import logging
import traceback
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.auth import verify_token
from app.core.database import engine
from app.api import documents, findings, dashboard, chat, memos

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pantau")

app = FastAPI(
    title="PANTAU API",
    description="Platform AI Transparansi dan Audit Keuangan Daerah",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def all_exceptions(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error("Unhandled exception: %s\n%s", exc, tb)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__, "traceback": tb.splitlines()[-5:]},
        headers={"Access-Control-Allow-Origin": "*"},
    )


protected = {"dependencies": [Depends(verify_token)]}

app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"], **protected)
app.include_router(findings.router, prefix="/api/v1/findings", tags=["findings"], **protected)
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"], **protected)
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"], **protected)
app.include_router(memos.router, prefix="/api/v1/memos", tags=["memos"], **protected)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "pantau-api"}


@app.get("/debug/db", tags=["health"])
async def debug_db():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 as ok"))
            row = result.fetchone()
            return {"db": "ok", "result": row[0] if row else None}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"db": "error", "error": str(e), "type": type(e).__name__},
        )
