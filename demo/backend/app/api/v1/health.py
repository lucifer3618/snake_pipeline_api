from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    service: str
    version: str


@router.get(
    "",
    response_model=HealthResponse,
    summary="Check API health",
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="final-demo-api",
        version="1.0.1",
    )
