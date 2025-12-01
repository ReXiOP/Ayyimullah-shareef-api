from pydantic import BaseModel
from typing import List, Optional

class EventDetailBase(BaseModel):
    detail: str

class EventDetailCreate(EventDetailBase):
    pass

class EventDetail(EventDetailBase):
    id: int
    event_id: int

    class Config:
        from_attributes = True

class EventBase(BaseModel):
    day: str

class EventCreate(EventBase):
    details: List[str]

class Event(EventBase):
    id: int
    month_id: int
    details: List[EventDetail] = []

    class Config:
        from_attributes = True

class MonthBase(BaseModel):
    month_bn: str
    month_en: str

class MonthCreate(MonthBase):
    events: List[EventCreate] = []

class Month(MonthBase):
    id: int
    events: List[Event] = []

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
