from celery import Celery
from src.core.config import settings

#CELERY CONFIGURATION
celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

#TEMPORARY TASK
@celery_app.task
def test_task(x, y):
    return x + y