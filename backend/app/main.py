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
from .services.extraction import load_model, is_model_loaded
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

    # MongoDB connection (optional, fail gracefully)
    if settings.MONGODB_URI:
        try:
            logger.info("Connecting to MongoDB...")
            await connect_db()
            logger.info("MongoDB connected ✓")
        except Exception as e:
            logger.warning("MongoDB connection failed: %s — continuing without persistence", e)
    else:
        logger.warning("MONGODB_URI not set — document storage disabled")

    # Load NER model (optional, fail gracefully)
    try:
        logger.info("Loading NER model...")
        load_model()
        if is_model_loaded():
            logger.info("NER model loaded ✓")
        else:
            logger.warning("NER model unavailable — rule-based extraction enabled")
    except Exception as e:
        logger.warning("NER model load failed: %s — rule-based extraction enabled", e)

    logger.info("=" * 60)
    logger.info("  Server ready — listening on http://0.0.0.0:7860")
    logger.info("=" * 60)
    yield

    # Shutdown
    if settings.MONGODB_URI:
        try:
            logger.info("Shutting down — closing MongoDB connection...")
            await close_db()
        except Exception as e:
            logger.warning("Error closing MongoDB: %s", e)
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
