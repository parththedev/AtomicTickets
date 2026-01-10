from fastapi import FastAPI
from src.routes import buying_router
from contextlib import asynccontextmanager
from src.redis.client import redis_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_manager.connect()
    yield
    await redis_manager.close()

version = "v1"

app = FastAPI(
    lifespan=lifespan,
    title="AtomicTickets",
    description="A flash-sale system that handles 1,000 concurrent requests for 10 tickets with zero race conditions or overselling",
    version=version
)

app.include_router(buying_router, prefix=f"/api/{version}/buying", tags=["buying"])

