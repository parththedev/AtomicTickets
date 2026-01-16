import time
from celery import Celery
from sqlalchemy import update
from src.core.config import settings
from src.db.session import SyncSessionLocal
from src.db.models import Event, Booking

# Configure Celery
celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

@celery_app.task(name="process_order")
def process_order(event_id: int, user_id: int):
    """
    Background task to finalize the order in Postgres.
    """
    print(f"📦 Processing order for Event {event_id} / User {user_id}")
    
    # Simulate payment process
    time.sleep(2) 
    
    # Database Operations
    with SyncSessionLocal() as session:
        # Boooking record creation
        new_booking = Booking(
            user_id=user_id,
            event_id=event_id,
            status="confirmed"
        )
        session.add(new_booking)
        
        # Decrement the Postgres Inventory
        stmt = (
            update(Event)
            .where(Event.id == event_id)
            .values(tickets_left=Event.tickets_left - 1)
        )
        session.execute(stmt)
        
        # Commit
        session.commit()
        print(f"✅ Order confirmed for Event {event_id}")
        
    return True