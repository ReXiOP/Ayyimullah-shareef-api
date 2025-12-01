from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Month(Base):
    __tablename__ = "months"

    id = Column(Integer, primary_key=True, index=True)
    month_bn = Column(String, index=True)
    month_en = Column(String, index=True)

    events = relationship("Event", back_populates="month", cascade="all, delete-orphan")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    month_id = Column(Integer, ForeignKey("months.id"))
    day = Column(String)

    month = relationship("Month", back_populates="events")
    details = relationship("EventDetail", back_populates="event", cascade="all, delete-orphan")

class EventDetail(Base):
    __tablename__ = "event_details"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    detail = Column(Text)

    event = relationship("Event", back_populates="details")
