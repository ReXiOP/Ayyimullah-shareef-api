import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from . import models, database, crud, schemas
from .routers import admin, auth, dashboard, public

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Ayyimullah Shareef API")

app.mount("/static", StaticFiles(directory="api/static"), name="static")

app.include_router(auth.router)
app.include_router(public.router)
app.include_router(admin.router)
app.include_router(dashboard.router)

@app.on_event("startup")
def startup_event():
    db = database.SessionLocal()
    try:
        # Check if we have any data
        if db.query(models.Month).count() == 0:
            print("Seeding database...")
            file_path = "file.json"
            if not os.path.exists(file_path):
                print(f"File {file_path} not found.")
                return
            
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            calendar_data = data.get("Aiyamullah_Shareef_Calendar", [])
            
            for month_data in calendar_data:
                events = []
                for event_data in month_data.get("events", []):
                    details = event_data.get("details", [])
                    events.append(schemas.EventCreate(day=event_data["day"], details=details))
                
                month_create = schemas.MonthCreate(
                    month_bn=month_data["month_bn"],
                    month_en=month_data["month_en"],
                    events=events
                )
                crud.create_month(db, month_create)
            
            # Create default admin user
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_password = os.getenv("ADMIN_PASSWORD", "password123")
            
            if not crud.get_user(db, admin_username):
                crud.create_user(db, schemas.UserCreate(username=admin_username, password=admin_password))
                print(f"Created default admin user: {admin_username}/{admin_password}")
                
            print("Database seeded successfully.")
    finally:
        db.close()
