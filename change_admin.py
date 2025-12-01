import os
import sys
from api import auth, crud, database, schemas
from dotenv import load_dotenv

load_dotenv()

def change_admin_password(new_username, new_password):
    db = database.SessionLocal()
    try:
        # Check if user exists
        user = crud.get_user(db, new_username)
        
        # If username is different from current admin in .env, we might be creating a new one
        # But here we just want to ensure THIS user has THIS password
        
        if user:
            print(f"Updating password for user: {new_username}")
            hashed_password = auth.get_password_hash(new_password)
            user.hashed_password = hashed_password
            db.commit()
            print("Password updated successfully.")
        else:
            print(f"User {new_username} not found. Creating new admin user.")
            crud.create_user(db, schemas.UserCreate(username=new_username, password=new_password))
            print("User created successfully.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python change_admin.py <username> <password>")
    else:
        change_admin_password(sys.argv[1], sys.argv[2])
