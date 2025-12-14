from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import asyncio
import threading
import logging

from app.database import engine, get_db, SessionLocal
from app.models import Base, User as UserModel, DeletedUser
from app import schemas
from app.email import send_welcome_email, send_goodbye_email

logger = logging.getLogger(__name__)

# Flag to control the listener thread
_listener_running = False


def email_listener():
    """
    Background task that polls the database for:
    1. New users without welcome emails
    2. Deleted users without goodbye emails
    Runs continuously and checks every 5 seconds.
    """
    global _listener_running
    logger.info("Email listener started")
    
    while _listener_running:
        try:
            db = SessionLocal()
            try:
                # Process welcome emails for new users
                new_users = db.query(UserModel).filter(
                    UserModel.welcome_email_sent == False
                ).all()
                
                for user in new_users:
                    logger.info(f"Sending welcome email to new user: {user.email}")
                    try:
                        send_welcome_email(user.email, user.name)
                        # Mark email as sent
                        user.welcome_email_sent = True
                        db.commit()
                        logger.info(f"Welcome email sent successfully to {user.email}")
                    except Exception as e:
                        logger.error(f"Failed to send welcome email to {user.email}: {e}")
                        db.rollback()
                
                # Process goodbye emails for deleted users
                deleted_users = db.query(DeletedUser).filter(
                    DeletedUser.goodbye_email_sent == False
                ).all()
                
                for deleted_user in deleted_users:
                    logger.info(f"Sending goodbye email to deleted user: {deleted_user.email}")
                    try:
                        send_goodbye_email(deleted_user.email, deleted_user.name)
                        # Delete the record after email is sent (data privacy)
                        db.delete(deleted_user)
                        db.commit()
                        logger.info(f"Goodbye email sent and record deleted for {deleted_user.email}")
                    except Exception as e:
                        logger.error(f"Failed to send goodbye email to {deleted_user.email}: {e}")
                        db.rollback()
                        
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in email listener: {e}")
        
        # Wait 5 seconds before checking again
        import time
        time.sleep(5)
    
    logger.info("Email listener stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _listener_running
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Start email listener thread
    _listener_running = True
    listener_thread = threading.Thread(target=email_listener, daemon=True)
    listener_thread.start()
    logger.info("Application startup complete, email listener running")
    
    yield
    
    # Stop listener on shutdown
    _listener_running = False
    logger.info("Application shutting down")


app = FastAPI(lifespan=lifespan)


# CORS (add this block)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/users", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Prevent duplicate emails
    existing = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Email already registered")

    # Create user welcome_email_sent = False
    db_user = UserModel(email=user.email, name=user.name, age=user.age)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Email will be sent automatically by the database listener
    logger.info(f"User created: {user.email}. Email listener will send welcome email.")

    return db_user


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Copy user to deleted_users table before deletion
    deleted_user_record = DeletedUser(
        email=user.email,
        name=user.name,
        goodbye_email_sent=False
    )
    db.add(deleted_user_record)
    
    # Delete the user from users table
    db.delete(user)
    db.commit()
    
    # Email will be sent automatically by the database listener
    logger.info(f"User deleted: {user.email}. Email listener will send goodbye email.")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
