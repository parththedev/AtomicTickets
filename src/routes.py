import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from src.db.session import AsyncSession, get_db
from src.db.models import Event
from src.db.schemas import EventRead, EventCreate, LoadTickets
from sqlalchemy.exc import IntegrityError
from redis.asyncio import Redis
from src.redis.client import redis_manager, get_redis_client
from src.worker.celery_app import process_order

buying_router = APIRouter()

@buying_router.get("/health")
async def health_check(db:AsyncSession = Depends(get_db)):
    return {
        "status": "alive"
    }

@buying_router.get("/", response_model=list[EventRead], status_code=status.HTTP_200_OK)
async def read_all_events(db:AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).order_by(Event.id.asc()))
    events = result.scalars().all()
    return events

@buying_router.post("/", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(payload:EventCreate,db:AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis_client)):
    new_event = Event(
    name=payload.name,
    total_tickets=payload.total_tickets,
    tickets_left=payload.total_tickets,  # correct
    active=payload.active
    )
    db.add(new_event)
    try:
        await db.commit()
        await db.refresh(new_event)
        redis_key = f"event:{new_event.id}:tickets"
        await redis.set(redis_key, new_event.total_tickets)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Event already exists!")
    await db.refresh(new_event)
    return new_event

@buying_router.patch("/{event_id}", response_model=EventRead, status_code=status.HTTP_202_ACCEPTED)
async def load_tickets(event_id:int, payload:LoadTickets, db:AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis_client)):
    result = await db.execute(select(Event).where(Event.id==event_id))
    event = result.scalar_one_or_none()
    if not event:  
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with {event_id} not found!")  
    event.total_tickets = payload.total_tickets
    event.tickets_left = payload.total_tickets 
    redis_key = f"event:{event.id}:tickets"
    await redis.set(redis_key, event.total_tickets)
    await db.commit()
    await db.refresh(event)
    return event

@buying_router.post("/naive-buy/{event_id}", response_model=EventRead,status_code=status.HTTP_200_OK)
async def naive_buy(event_id:int, db:AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.id==event_id))
    event = result.scalar_one()
    if event.tickets_left <= 0:
        raise HTTPException(409, "Sold out")
    
    await asyncio.sleep(0.1)

    event.tickets_left -= 1
    await db.commit()
    return event

@buying_router.post("/atomic-buy/{event_id}", status_code=status.HTTP_200_OK)
async def atomic_buy(event_id: int):
    redis_key = f"event:{event_id}:tickets"
    try:
        result = await redis_manager.buy_ticket_script(keys=[redis_key])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(e)}")

    if result == 1:
        process_order.delay(event_id, 1)
        return {"status": "purchased", "message": "Ticket reserved! Processing payment..."}
    
    elif result == 0:
        raise HTTPException(status_code=400, detail="Sold out")
    
    elif result == -1:
        raise HTTPException(status_code=404, detail="Event not found in Redis")
        
    return {"status": "unknown"}    
