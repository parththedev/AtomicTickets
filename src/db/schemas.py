from pydantic import BaseModel, ConfigDict
from datetime import datetime

class EventCreate(BaseModel):
    name: str
    total_tickets: int 
    active:bool = True

class EventRead(BaseModel):
    id: int
    name: str
    total_tickets: int
    tickets_left: int 
    active: bool
    created_at: datetime    
    model_config = ConfigDict(from_attributes=True)

class LoadTickets(BaseModel):
    total_tickets: int