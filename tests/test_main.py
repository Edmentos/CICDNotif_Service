import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.main import app
from app.models import Base, Notification

TEST_DB_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_db():
    """Mock database session for testing without actual DB operations"""
    return MagicMock()


class TestHealthCheck:
    @patch('app.main.check_rabbitmq_connection')
    @patch.dict('os.environ', {'SMTP_HOST': 'smtp.example.com'})
    def test_health_check_all_healthy(self, mock_rabbitmq, client):
        mock_rabbitmq.return_value = True
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "rabbitmq" in data
        assert "smtp_configured" in data
    
    @patch('app.main.check_rabbitmq_connection')
    def test_health_check_rabbitmq_down(self, mock_rabbitmq, client):
        mock_rabbitmq.return_value = False
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["rabbitmq"] == "unhealthy"
    
    @patch('app.main.check_rabbitmq_connection')
    @patch('app.main.SessionLocal')
    def test_health_check_database_unhealthy(self, mock_session_local, mock_rabbitmq, client):
        # Mock database connection failure
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Database connection failed")
        mock_session_local.return_value = mock_db
        mock_rabbitmq.return_value = True
        
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "unhealthy"
    
    @patch.dict('os.environ', {}, clear=True)
    @patch('app.main.check_rabbitmq_connection')
    def test_health_check_smtp_not_configured(self, mock_rabbitmq, client):
        mock_rabbitmq.return_value = True
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["smtp_configured"] == False


class TestNotificationEndpoints:
    """Test notification-related endpoints - these are no longer needed as endpoints were removed"""
    pass
