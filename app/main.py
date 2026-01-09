from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading
import logging
import os

from app.database import engine, SessionLocal
from app.models import Base
from app.rabbitmq import check_rabbitmq_connection
from app.worker import start_consumer

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # setup DB tables on startup
    Base.metadata.create_all(bind=engine)
    
    # spin up background thread to listen for rabbitmq messages
    rabbitmq_thread = threading.Thread(target=start_consumer, daemon=True)
    rabbitmq_thread.start()
    logger.info("RabbitMQ consumer started")
    
    logger.info("Application startup complete")
    
    yield
    
    logger.info("Application shutting down")


app = FastAPI(lifespan=lifespan)


# allow cors for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)


# basic health endpoint to check if everything's running
@app.get("/health")
def health_check():
    # try connecting to db
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "healthy"
    except:
        db_status = "unhealthy"
    
    # check rabbitmq
    rabbitmq_status = "healthy" if check_rabbitmq_connection() else "not connected"
    
    # see if smtp env vars are set
    smtp_configured = bool(os.getenv("SMTP_HOST"))
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "rabbitmq": rabbitmq_status,
        "smtp_configured": smtp_configured
    }
