from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import database, schemas, crud, auth, models

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_current_user)]
)

@router.post("/months/", response_model=schemas.Month)
def create_month(month: schemas.MonthCreate, db: Session = Depends(database.get_db)):
    return crud.create_month(db=db, month=month)

@router.delete("/months/{month_id}", response_model=schemas.Month)
def delete_month(month_id: int, db: Session = Depends(database.get_db)):
    return crud.delete_month(db=db, month_id=month_id)

@router.put("/months/{month_id}", response_model=schemas.Month)
def update_month(month_id: int, month: schemas.MonthBase, db: Session = Depends(database.get_db)):
    return crud.update_month(db=db, month_id=month_id, month=month)

@router.post("/months/{month_id}/events/", response_model=schemas.Event)
def create_event(month_id: int, event: schemas.EventCreate, db: Session = Depends(database.get_db)):
    return crud.create_event(db=db, month_id=month_id, event=event)

@router.delete("/events/{event_id}", response_model=schemas.Event)
def delete_event(event_id: int, db: Session = Depends(database.get_db)):
    return crud.delete_event(db=db, event_id=event_id)

@router.post("/events/{event_id}/details/", response_model=schemas.EventDetail)
def add_detail(event_id: int, detail: schemas.EventDetailCreate, db: Session = Depends(database.get_db)):
    return crud.add_detail(db=db, event_id=event_id, detail=detail.detail)

@router.delete("/details/{detail_id}", response_model=schemas.EventDetail)
def delete_detail(detail_id: int, db: Session = Depends(database.get_db)):
    return crud.delete_detail(db=db, detail_id=detail_id)
