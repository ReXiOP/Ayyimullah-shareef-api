from sqlalchemy.orm import Session
from sqlalchemy import or_
from . import models, schemas, auth

def get_user(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_months(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Month).offset(skip).limit(limit).all()

def get_month(db: Session, month_id: int):
    return db.query(models.Month).filter(models.Month.id == month_id).first()

def create_month(db: Session, month: schemas.MonthCreate):
    db_month = models.Month(month_bn=month.month_bn, month_en=month.month_en)
    db.add(db_month)
    db.commit()
    db.refresh(db_month)
    
    for event_data in month.events:
        db_event = models.Event(day=event_data.day, month_id=db_month.id)
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        
        for detail in event_data.details:
            db_detail = models.EventDetail(detail=detail, event_id=db_event.id)
            db.add(db_detail)
        db.commit()
        
    db.refresh(db_month)
    return db_month

def delete_month(db: Session, month_id: int):
    db_month = db.query(models.Month).filter(models.Month.id == month_id).first()
    if db_month:
        db.delete(db_month)
        db.commit()
    return db_month

def update_month(db: Session, month_id: int, month: schemas.MonthBase):
    db_month = db.query(models.Month).filter(models.Month.id == month_id).first()
    if db_month:
        db_month.month_bn = month.month_bn
        db_month.month_en = month.month_en
        db.commit()
        db.refresh(db_month)
    return db_month

def create_event(db: Session, month_id: int, event: schemas.EventCreate):
    db_event = models.Event(day=event.day, month_id=month_id)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    for detail in event.details:
        db_detail = models.EventDetail(detail=detail, event_id=db_event.id)
        db.add(db_detail)
    db.commit()
    db.refresh(db_event)
    return db_event

def delete_event(db: Session, event_id: int):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event:
        db.delete(db_event)
        db.commit()
    return db_event

def add_detail(db: Session, event_id: int, detail: str):
    db_detail = models.EventDetail(detail=detail, event_id=event_id)
    db.add(db_detail)
    db.commit()
    db.refresh(db_detail)
    return db_detail

def delete_detail(db: Session, detail_id: int):
    db_detail = db.query(models.EventDetail).filter(models.EventDetail.id == detail_id).first()
    if db_detail:
        db.delete(db_detail)
        db.commit()
    return db_detail

def to_bangla_digits(number_str: str) -> str:
    eng_to_bn = {
        '0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪',
        '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯'
    }
    return "".join(eng_to_bn.get(char, char) for char in number_str)

def get_events_by_date(db: Session, month_id: int, day: str):
    # Try exact match first
    events = db.query(models.Event).filter(models.Event.month_id == month_id, models.Event.day == day).all()
    if events:
        return events
        
    # Try converting to Bangla digits
    day_bn = to_bangla_digits(day)
    if day_bn != day:
        return db.query(models.Event).filter(models.Event.month_id == month_id, models.Event.day == day_bn).all()
        
    return []

def search_details(db: Session, query: str):
    # Search for event details that match the query
    return db.query(models.EventDetail).filter(models.EventDetail.detail.ilike(f"%{query}%")).all()
