from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from .. import database, schemas, crud

router = APIRouter(
    prefix="/api",
    tags=["public"]
)

@router.get("/months", response_model=List[schemas.Month])
def read_months(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    months = crud.get_months(db, skip=skip, limit=limit)
    return months

@router.get("/months/{month_id}", response_model=schemas.Month)
def read_month(month_id: int, db: Session = Depends(database.get_db)):
    return crud.get_month(db, month_id=month_id)

@router.get("/months/{month_id}/days/{day}", response_model=List[schemas.Event])
def read_events_by_date(month_id: int, day: str, db: Session = Depends(database.get_db)):
    return crud.get_events_by_date(db, month_id=month_id, day=day)

@router.get("/search", response_model=List[schemas.EventDetail])
def search_events(q: str = Query(..., min_length=3), db: Session = Depends(database.get_db)):
    return crud.search_details(db, query=q)
