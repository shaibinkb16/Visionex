from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

_client: AsyncIOMotorClient = None


def get_db():
    return _client["doc_extraction"]


async def connect_db():
    global _client
    _client = AsyncIOMotorClient(settings.MONGODB_URI)


async def close_db():
    global _client
    if _client:
        _client.close()
