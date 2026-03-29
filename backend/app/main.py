import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .core.config import settings
from .core.dependencies import connect_db, close_db
from .services.extraction import load_model
from .api import documents, extract, query, health

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
# Silence noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("multipart").setLevel(logging.WARNING)
logging.getLogger("easyocr").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  Visionex Extraction API — starting up")
    logger.info("=" * 60)
    logger.info("ENV          : %s", settings.ENV)
    logger.info("CORS origin  : %s", settings.CORS_ORIGIN)
    logger.info("HF model     : %s", settings.HF_MODEL_ID)
    logger.info("Conf threshold: %.2f", settings.CONFIDENCE_THRESHOLD)

    logger.info("Connecting to MongoDB...")
    await connect_db()
    logger.info("MongoDB connected ✓")

    logger.info("Loading NER model...")
    load_model()

    logger.info("=" * 60)
    logger.info("  Server ready — listening on http://0.0.0.0:8000")
    logger.info("=" * 60)
    yield

    logger.info("Shutting down — closing MongoDB connection...")
    await close_db()
    logger.info("Shutdown complete.")


app = FastAPI(title="Visionex Extraction API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(extract.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(health.router)
