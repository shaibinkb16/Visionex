from fastapi import APIRouter
from ..services.extraction import is_model_loaded
from ..core.dependencies import get_db
from ..models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    db_ok = False
    try:
        await get_db().command("ping")
        db_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        model_loaded=is_model_loaded(),
        db_connected=db_ok,
    )
