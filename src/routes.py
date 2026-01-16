import asyncio
import random
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select, delete, update
from sqlalchemy.exc import IntegrityError

from src.db.session import get_db, AsyncSession
from src.db.models import Event, Booking
from src.db.schemas import EventRead, EventCreate, LoadTickets
from src.redis.client import redis_manager, get_redis_client
from redis.asyncio import Redis
from src.worker.celery_app import process_order

buying_router = APIRouter()

@buying_router.get("/health")
async def health_check():
    return {"status": "alive"}

@buying_router.get("/", response_model=list[EventRead])
async def read_all_events(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).order_by(Event.id.asc()))
    return result.scalars().all()

@buying_router.post("/", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client)
):
    new_event = Event(
        name=payload.name,
        total_tickets=payload.total_tickets,
        tickets_left=payload.total_tickets,
        active=payload.active
    )
    db.add(new_event)
    try:
        await db.commit()
        await db.refresh(new_event)
        # Seed Redis immediately
        await redis.set(f"event:{new_event.id}:tickets", new_event.total_tickets)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Event creation failed")
    
    return new_event

# --- NAIVE ENDPOINT (INTENTIONALLY BROKEN) ---
@buying_router.post("/naive-buy/{event_id}", status_code=200)
async def naive_buy(event_id: int, db: AsyncSession = Depends(get_db)):
    # Fetch Event
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.tickets_left <= 0:
        raise HTTPException(status_code=400, detail="Sold out")
    
    # this is network latency or payment gateway processing
    await asyncio.sleep(0.1) 

    # Update DB
    event.tickets_left -= 1
    
    # Simulate a random user (1000-9999) to make DB look realistic
    simulated_user_id = random.randint(1000, 9999)
    
    booking = Booking(user_id=simulated_user_id, event_id=event_id, status="confirmed")
    db.add(booking)

    await db.commit()
    return {"status": "purchased", "left": event.tickets_left}

# --- ATOMIC ENDPOINT (FIXED) ---
@buying_router.post("/atomic-buy/{event_id}", status_code=200)
async def atomic_buy(
    event_id: int, 
    x_idempotency_key: str = Header(None, alias="X-Idempotency-Key")
):
    # Validate Header
    if not x_idempotency_key:
        raise HTTPException(status_code=422, detail="Missing Idempotency Key")

    redis_key = f"event:{event_id}:tickets"
    idem_key = f"idempotency:{x_idempotency_key}"
    
    try:
        # Run Lua Script
        result = await redis_manager.buy_ticket_script(keys=[redis_key, idem_key])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(e)}")

    if result == 1:
        # Success: Trigger Async Worker
        # Simulate random user for realistic data
        simulated_user_id = random.randint(1000, 9999)
        process_order.delay(event_id, simulated_user_id)
        return {"status": "purchased"}
    
    elif result == 2:
        return {"status": "purchased", "message": "Idempotent Replay"}
    
    elif result == 0:
        raise HTTPException(status_code=400, detail="Sold out")
    
    elif result == -1:
        raise HTTPException(status_code=404, detail="Event not found in Redis")

    return {"status": "error"}

# --- RESET ENDPOINT ---
@buying_router.post("/reset/{event_id}")
async def reset_event(
    event_id: int, 
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client)
):
    # Get original capacity
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    reset_amount = event.total_tickets  

    # Clear Bookings in Postgres
    await db.execute(delete(Booking).where(Booking.event_id == event_id))
    
    # Reset Inventory in Postgres
    await db.execute(
        update(Event)
        .where(Event.id == event_id)
        .values(tickets_left=reset_amount)
    )
    
    # Reset Redis
    await redis.set(f"event:{event_id}:tickets", reset_amount)
    
    # Clear ALL Idempotency Keys (For demo restart capability)
    keys = await redis.keys("idempotency:*")
    if keys:
        await redis.delete(*keys)
    
    await db.commit()
    return {"status": "reset", "tickets": reset_amount}