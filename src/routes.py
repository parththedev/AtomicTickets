from fastapi import APIRouter

buying_router = APIRouter()

@buying_router.get("/health")
async def health_check():
    return {
        "status": "alive"
    }