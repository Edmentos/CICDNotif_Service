from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.models import Base, User as UserModel
from app import schemas
from app.email import send_welcome_email


# Replacing @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)


# CORS (add this block)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-friendly; tighten in prod
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/users", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Prevent duplicate emails
    existing = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Email already registered")

    db_user = UserModel(email=user.email, name=user.name, age=user.age)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # send welcome email in background (no-op if SMTP not configured)
    # schedule welcome email in background (no-op if SMTP not configured)
    try:
        background_tasks.add_task(send_welcome_email, db_user.email, db_user.name)
    except Exception:
        # scheduling failed; ignore so user creation succeeds
        pass

    return db_user


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
