from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import threading
import logging
import os
from sqlalchemy import text

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
def health_check(response: Response):
    health_issues = []
    
    # try connecting to db
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
        health_issues.append("database")
    
    # check rabbitmq
    rabbitmq_connected = check_rabbitmq_connection()
    rabbitmq_status = "healthy" if rabbitmq_connected else "unhealthy"
    if not rabbitmq_connected:
        health_issues.append("rabbitmq")
    
    # see if smtp env vars are set
    smtp_configured = bool(os.getenv("SMTP_HOST"))
    
    # determine overall health
    is_healthy = len(health_issues) == 0
    
    # set http status code based on health
    if not is_healthy:
        response.status_code = 503
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "database": db_status,
        "rabbitmq": rabbitmq_status,
        "smtp_configured": smtp_configured
    }
