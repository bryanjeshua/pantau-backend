from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.auth import verify_token
from app.api import documents, findings, dashboard, chat, memos

app = FastAPI(
    title="PANTAU API",
    description="Platform AI Transparansi dan Audit Keuangan Daerah",
    version="0.1.0",
)

_origins = [o.strip() for o in settings.FRONTEND_URL.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
