from fastapi import FastAPI
from src.routes import buying_router

version = "v1"

app = FastAPI(
    title="AtomicTickets",
    description="A flash-sale system that handles 1,000 concurrent requests for 10 tickets with zero race conditions or overselling",
    version=version
)

app.include_router(buying_router, prefix=f"/api/{version}/buying", tags=["buying"])

