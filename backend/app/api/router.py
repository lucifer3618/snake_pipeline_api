from fastapi import APIRouter, Depends

from app.api.v1 import health, predictions
from app.core.security import enforce_rate_limit, require_api_key


api_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_api_key), Depends(enforce_rate_limit)],
)

api_router.include_router(health.router)
api_router.include_router(predictions.router)
