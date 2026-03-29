from motor.motor_asyncio import AsyncIOMotorClient
import logging
from .config import settings

_client: AsyncIOMotorClient = None
logger = logging.getLogger(__name__)


def get_db():
    if _client is None:
        raise RuntimeError("MongoDB not connected. Set MONGODB_URI in environment variables.")
    return _client["doc_extraction"]


async def connect_db():
    global _client
    if not settings.MONGODB_URI:
        logger.warning("MONGODB_URI not set — document storage disabled")
        return
    try:
        _client = AsyncIOMotorClient(settings.MONGODB_URI)
        # Test connection
        await _client.admin.command("ping")
        logger.info("MongoDB connection successful")
    except Exception as e:
        logger.error("Failed to connect to MongoDB: %s", e)
        _client = None


async def close_db():
    global _client
    if _client:
        try:
            _client.close()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error("Error closing MongoDB connection: %s", e)
