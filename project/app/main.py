from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean, func
import hashlib
from datetime import datetime, timedelta
import uuid

from .database import engine, SessionLocal, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth & User API")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    is_active = Column(Boolean, default=True)

class UserCreate(BaseModel):
    username: str = Field(..., description="Логин пользователя")
    password: str = Field(..., description="Пароль в открытом виде")

class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    status: str
    message: str
    session_token: Optional[str] = None

sessions_db = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@app.get("/", response_class=HTMLResponse)
def read_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/v1/users/", response_model=List[UserResponse], status_code=status.HTTP_200_OK)
def get_users(db: Session = Depends(get_db)):
    return db.query(UserDB).all()

@app.get("/api/v1/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/v1/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = UserDB(username=user.username, password_hash=get_hash(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.delete("/api/v1/users/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

@app.post("/api/v1/auth/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == req.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.password_hash != get_hash(req.password):
        raise HTTPException(status_code=400, detail="Invalid password")
    
    session_token = str(uuid.uuid4())
    sessions_db[session_token] = {
        "username": req.username,
        "last_activity": datetime.now()
    }
    return {"status": "success", "message": "Access granted", "session_token": session_token}

# --- НОВЫЙ ЭНДПОИНТ ДЛЯ СТАТИСТИКИ (ГРАФИКОВ) ---
@app.get("/api/v1/stats")
def get_stats(db: Session = Depends(get_db)):
    total_users = db.query(UserDB).count()
    active_users = db.query(UserDB).filter(UserDB.is_active == True).count()
    inactive_users = total_users - active_users
    
    return {
        "total": total_users,
        "active": active_users,
        "inactive": inactive_users
    }