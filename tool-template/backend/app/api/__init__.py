from fastapi import APIRouter

from .process_route import router as process_router

router = APIRouter()
router.include_router(process_router)


@router.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}
