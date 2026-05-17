import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import diagnose, health

# Make sure app loggers (e.g. app.services.gemini) actually emit to stdout
# alongside uvicorn's access log.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

settings = get_settings()

app = FastAPI(
    title="몰루? API",
    version="0.1.0",
    description="멀티모달 AI 가이드 백엔드 — Gemini 진단. Tavily/CRAG는 v0.2에서.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=600,
)

app.include_router(health.router)
app.include_router(diagnose.router)
