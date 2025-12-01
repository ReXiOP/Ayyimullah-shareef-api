from fastapi import APIRouter, Request, Depends, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .. import database, crud, auth, models

templates = Jinja2Templates(directory="api/templates")

router = APIRouter(
    include_in_schema=False
)

def get_current_user_from_cookie(request: Request, db: Session = Depends(database.get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        # Remove "Bearer " prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        user = auth.get_current_user(token, db)
        return user
    except:
        return None

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login_submit(request: Request, db: Session = Depends(database.get_db)):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    
    user = crud.get_user(db, username=username)
    if not user or not auth.verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    
    access_token = auth.create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(database.get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    months = crud.get_months(db)
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "months": months})

@router.get("/dashboard/months/{month_id}", response_class=HTMLResponse)
async def month_detail(request: Request, month_id: int, db: Session = Depends(database.get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    month = crud.get_month(db, month_id)
    if not month:
        return RedirectResponse(url="/dashboard")
        
    return templates.TemplateResponse("month_detail.html", {"request": request, "user": user, "month": month})

@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/dashboard")
