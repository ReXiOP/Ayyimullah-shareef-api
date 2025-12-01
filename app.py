import os
import json
import sys
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request, Query, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Database Setup ---
# Use DATABASE_URL from env if available (for Vercel/Postgres), otherwise fallback to SQLite
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Handle special case for Postgres URL starting with "postgres://" (SQLAlchemy needs "postgresql://")
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Models ---
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

# --- Schemas ---
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

class EventSchema(EventBase):
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

class MonthSchema(MonthBase):
    id: int
    events: List[EventSchema] = []

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserSchema(UserBase):
    id: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- Auth Logic ---
# SECRET_KEY should be in env variables in production
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

# --- CRUD Operations ---
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user_db(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_months(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Month).offset(skip).limit(limit).all()

def get_month(db: Session, month_id: int):
    return db.query(Month).filter(Month.id == month_id).first()

def create_month_db(db: Session, month: MonthCreate):
    db_month = Month(month_bn=month.month_bn, month_en=month.month_en)
    db.add(db_month)
    db.commit()
    db.refresh(db_month)
    
    for event_data in month.events:
        db_event = Event(day=event_data.day, month_id=db_month.id)
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        
        for detail in event_data.details:
            db_detail = EventDetail(detail=detail, event_id=db_event.id)
            db.add(db_detail)
        db.commit()
        
    db.refresh(db_month)
    return db_month

def delete_month_db(db: Session, month_id: int):
    db_month = db.query(Month).filter(Month.id == month_id).first()
    if db_month:
        db.delete(db_month)
        db.commit()
    return db_month

def update_month_db(db: Session, month_id: int, month: MonthBase):
    db_month = db.query(Month).filter(Month.id == month_id).first()
    if db_month:
        db_month.month_bn = month.month_bn
        db_month.month_en = month.month_en
        db.commit()
        db.refresh(db_month)
    return db_month

def create_event_db(db: Session, month_id: int, event: EventCreate):
    db_event = Event(day=event.day, month_id=month_id)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    for detail in event.details:
        db_detail = EventDetail(detail=detail, event_id=db_event.id)
        db.add(db_detail)
    db.commit()
    db.refresh(db_event)
    return db_event

def delete_event_db(db: Session, event_id: int):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if db_event:
        db.delete(db_event)
        db.commit()
    return db_event

def add_detail_db(db: Session, event_id: int, detail: str):
    db_detail = EventDetail(detail=detail, event_id=event_id)
    db.add(db_detail)
    db.commit()
    db.refresh(db_detail)
    return db_detail

def delete_detail_db(db: Session, detail_id: int):
    db_detail = db.query(EventDetail).filter(EventDetail.id == detail_id).first()
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
    events = db.query(Event).filter(Event.month_id == month_id, Event.day == day).all()
    if events:
        return events
        
    # Try converting to Bangla digits
    day_bn = to_bangla_digits(day)
    if day_bn != day:
        return db.query(Event).filter(Event.month_id == month_id, Event.day == day_bn).all()
        
    return []

def search_details(db: Session, query: str):
    return db.query(EventDetail).filter(EventDetail.detail.ilike(f"%{query}%")).all()

# --- App Initialization ---
app = FastAPI(title="Ayyimullah Shareef API")

# Mount static files
# Ensure api/static exists or create it
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "api", "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Fix template directory for Vercel
# Vercel might change the working directory, so we need to be robust
base_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(base_dir, "api", "templates")
templates = Jinja2Templates(directory=templates_dir)

# --- Routers ---

# 1. Auth Router
auth_router = APIRouter(tags=["authentication"])

@auth_router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_username(db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

app.include_router(auth_router)

# 2. Public Router
public_router = APIRouter(prefix="/api", tags=["public"])

@public_router.get("/months", response_model=List[MonthSchema])
def read_months(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    months = get_months(db, skip=skip, limit=limit)
    return months

@public_router.get("/months/{month_id}", response_model=MonthSchema)
def read_month(month_id: int, db: Session = Depends(get_db)):
    return get_month(db, month_id=month_id)

@public_router.get("/months/{month_id}/days/{day}", response_model=List[EventSchema])
def read_events_by_date_route(month_id: int, day: str, db: Session = Depends(get_db)):
    return get_events_by_date(db, month_id=month_id, day=day)

@public_router.get("/search", response_model=List[EventDetail])
def search_events_route(q: str = Query(..., min_length=3), db: Session = Depends(get_db)):
    return search_details(db, query=q)

app.include_router(public_router)

# 3. Admin Router
admin_router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_user)])

@admin_router.post("/months/", response_model=MonthSchema)
def create_month_route(month: MonthCreate, db: Session = Depends(get_db)):
    return create_month_db(db=db, month=month)

@admin_router.delete("/months/{month_id}", response_model=MonthSchema)
def delete_month_route(month_id: int, db: Session = Depends(get_db)):
    return delete_month_db(db=db, month_id=month_id)

@admin_router.put("/months/{month_id}", response_model=MonthSchema)
def update_month_route(month_id: int, month: MonthBase, db: Session = Depends(get_db)):
    return update_month_db(db=db, month_id=month_id, month=month)

@admin_router.post("/months/{month_id}/events/", response_model=EventSchema)
def create_event_route(month_id: int, event: EventCreate, db: Session = Depends(get_db)):
    return create_event_db(db=db, month_id=month_id, event=event)

@admin_router.delete("/events/{event_id}", response_model=EventSchema)
def delete_event_route(event_id: int, db: Session = Depends(get_db)):
    return delete_event_db(db=db, event_id=event_id)

@admin_router.post("/events/{event_id}/details/", response_model=EventDetail)
def add_detail_route(event_id: int, detail: EventDetailCreate, db: Session = Depends(get_db)):
    return add_detail_db(db=db, event_id=event_id, detail=detail.detail)

@admin_router.delete("/details/{detail_id}", response_model=EventDetail)
def delete_detail_route(detail_id: int, db: Session = Depends(get_db)):
    return delete_detail_db(db=db, detail_id=detail_id)

app.include_router(admin_router)

# 4. Dashboard Router
dashboard_router = APIRouter(include_in_schema=False)

def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        if token.startswith("Bearer "):
            token = token[7:]
        user = None
        # We need to call get_current_user but it's async and depends on Depends
        # So we replicate the logic slightly or use a helper
        # Since we are in a sync context (or async), let's just decode manually
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username:
             user = db.query(User).filter(User.username == username).first()
        return user
    except:
        return None

@dashboard_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@dashboard_router.post("/login")
async def login_submit(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    
    user = get_user_by_username(db, username=username)
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    
    access_token = create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@dashboard_router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response

@dashboard_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    months = get_months(db)
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "months": months})

@dashboard_router.get("/dashboard/months/{month_id}", response_class=HTMLResponse)
async def month_detail_dashboard(request: Request, month_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    month = get_month(db, month_id)
    if not month:
        return RedirectResponse(url="/dashboard")
        
    return templates.TemplateResponse("month_detail.html", {"request": request, "user": user, "month": month})

@dashboard_router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/dashboard")

app.include_router(dashboard_router)

# --- Startup Event ---
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        # Create tables on startup
        Base.metadata.create_all(bind=engine)
        
        # Check if we have any data
        # In SQLAlchemy 1.4/2.0, query(Model) should work if Model is a class
        # The error suggests Month might not be recognized as a mapped class or similar
        # Let's try select(Month) style or just ensure it's correct
        if db.query(Month).first() is None:
            print("Seeding database...")
            # Use absolute path relative to this file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(base_dir, "file.json")
            
            if not os.path.exists(file_path):
                print(f"File {file_path} not found. CWD: {os.getcwd()}")
                return
            
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            calendar_data = data.get("Aiyamullah_Shareef_Calendar", [])
            
            for month_data in calendar_data:
                events = []
                for event_data in month_data.get("events", []):
                    details = event_data.get("details", [])
                    events.append(EventCreate(day=event_data["day"], details=details))
                
                month_create = MonthCreate(
                    month_bn=month_data["month_bn"],
                    month_en=month_data["month_en"],
                    events=events
                )
                create_month_db(db, month_create)
            
            # Create default admin user
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_password = os.getenv("ADMIN_PASSWORD", "password123")
            
            if not get_user_by_username(db, admin_username):
                create_user_db(db, UserCreate(username=admin_username, password=admin_password))
                print(f"Created default admin user: {admin_username}")
                
            print("Database seeded successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
