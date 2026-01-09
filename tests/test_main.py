import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

from app.main import app, get_db
from app.models import Base, User as UserModel, DeletedUser, Notification

TEST_DB_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(bind=engine)


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_db():
    """Mock database session for testing without actual DB operations"""
    return MagicMock()


class TestCreateUser:
    def test_create_user_invalid_email(self, client):
        response = client.post("/users", json={
            "email": "not-an-email",
            "name": "Test User",
            "age": 25
        })
        assert response.status_code == 422
    
    def test_create_user_negative_age(self, client):
        response = client.post("/users", json={
            "email": "test@example.com",
            "name": "Test User",
            "age": -5
        })
        assert response.status_code == 422
    
    def test_create_user_missing_name(self, client):
        response = client.post("/users", json={
            "email": "test@example.com",
            "age": 25
        })
        assert response.status_code == 422
    
    def test_create_user_missing_age(self, client):
        response = client.post("/users", json={
            "email": "test@example.com",
            "name": "Test User"
        })
        assert response.status_code == 422
    
    def test_create_user_missing_email(self, client):
        response = client.post("/users", json={
            "name": "Test User",
            "age": 25
        })
        assert response.status_code == 422


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
        assert "email_listener_running" in data
    
    @patch('app.main.check_rabbitmq_connection')
    def test_health_check_rabbitmq_down(self, mock_rabbitmq, client):
        mock_rabbitmq.return_value = False
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["rabbitmq"] == "not connected"
    
    @patch('app.main.check_rabbitmq_connection')
    @patch('app.main.SessionLocal')
    def test_health_check_database_unhealthy(self, mock_session_local, mock_rabbitmq, client):
        # Mock database connection failure
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Database connection failed")
        mock_session_local.return_value = mock_db
        mock_rabbitmq.return_value = True
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "unhealthy"
    
    @patch.dict('os.environ', {}, clear=True)
    @patch('app.main.check_rabbitmq_connection')
    def test_health_check_smtp_not_configured(self, mock_rabbitmq, client):
        mock_rabbitmq.return_value = True
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["smtp_configured"] == False
        assert "email_listener_running" in data


class TestNotificationEndpoints:
    """Test notification-related endpoints with mocked database"""
    
    def test_get_user_notifications_success(self, client, mock_db):
        # Create mock notifications
        mock_notif1 = MagicMock(spec=Notification)
        mock_notif1.id = 1
        mock_notif1.user_email = "test@example.com"
        mock_notif1.notification_type = "welcome"
        mock_notif1.subject = "Welcome!"
        mock_notif1.message = "Test notification 1"
        mock_notif1.is_read = False
        mock_notif1.delivered = True
        mock_notif1.sent_at = datetime(2026, 1, 9, 12, 0, 0)
        
        mock_notif2 = MagicMock(spec=Notification)
        mock_notif2.id = 2
        mock_notif2.user_email = "test@example.com"
        mock_notif2.notification_type = "info"
        mock_notif2.subject = "Info"
        mock_notif2.message = "Test notification 2"
        mock_notif2.is_read = True
        mock_notif2.delivered = True
        mock_notif2.sent_at = datetime(2026, 1, 8, 12, 0, 0)
        
        # Mock query chain
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_notif1, mock_notif2]
        mock_db.query.return_value = mock_query
        
        # Override get_db to return mock
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/api/notifications/test@example.com")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["message"] == "Test notification 1"
        finally:
            app.dependency_overrides.clear()
    
    def test_get_user_notifications_not_found(self, client, mock_db):
        # Mock empty result
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/api/notifications/nonexistent@example.com")
            assert response.status_code == 404
            assert response.json()["detail"] == "No notifications found for this email"
        finally:
            app.dependency_overrides.clear()
    
    def test_get_unread_notifications(self, client, mock_db):
        # Create mock unread notification
        mock_notif = MagicMock(spec=Notification)
        mock_notif.id = 1
        mock_notif.user_email = "test@example.com"
        mock_notif.notification_type = "alert"
        mock_notif.subject = "Unread Alert"
        mock_notif.message = "Unread notification"
        mock_notif.is_read = False
        mock_notif.delivered = True
        mock_notif.sent_at = datetime(2026, 1, 9, 12, 0, 0)
        
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_notif]
        mock_db.query.return_value = mock_query
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/api/notifications/test@example.com/unread")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["is_read"] == False
        finally:
            app.dependency_overrides.clear()
    
    def test_get_unread_notifications_empty(self, client, mock_db):
        # Mock empty unread notifications
        mock_query = MagicMock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.get("/api/notifications/test@example.com/unread")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 0
        finally:
            app.dependency_overrides.clear()
    
    def test_mark_notification_read_success(self, client, mock_db):
        # Create mock notification
        mock_notif = MagicMock(spec=Notification)
        mock_notif.id = 1
        mock_notif.user_email = "test@example.com"
        mock_notif.notification_type = "info"
        mock_notif.subject = "Test Subject"
        mock_notif.message = "Test notification"
        mock_notif.is_read = False
        mock_notif.delivered = True
        mock_notif.sent_at = datetime(2026, 1, 9, 12, 0, 0)
        
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_notif
        mock_db.query.return_value = mock_query
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.patch("/api/notifications/1", json={"is_read": True})
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            # Verify the is_read was set
            assert mock_notif.is_read == True
        finally:
            app.dependency_overrides.clear()
    
    def test_mark_notification_unread(self, client, mock_db):
        # Create mock notification that is read
        mock_notif = MagicMock(spec=Notification)
        mock_notif.id = 2
        mock_notif.user_email = "test@example.com"
        mock_notif.notification_type = "info"
        mock_notif.subject = "Test Subject"
        mock_notif.message = "Test notification"
        mock_notif.is_read = True
        mock_notif.delivered = True
        mock_notif.sent_at = datetime(2026, 1, 9, 12, 0, 0)
        
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_notif
        mock_db.query.return_value = mock_query
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.patch("/api/notifications/2", json={"is_read": False})
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 2
            # Verify the is_read was set to False
            assert mock_notif.is_read == False
        finally:
            app.dependency_overrides.clear()
    
    def test_mark_notification_read_not_found(self, client, mock_db):
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.patch("/api/notifications/999", json={"is_read": True})
            assert response.status_code == 404
            assert response.json()["detail"] == "Notification not found"
        finally:
            app.dependency_overrides.clear()
    



class TestUserEndpoints:
    """Test user CRUD endpoints with mocked database"""
    
    def test_create_user_success(self, client, mock_db):
        # Mock no existing user
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Mock created user
        mock_user = MagicMock(spec=UserModel)
        mock_user.id = 1
        mock_user.email = "newuser@example.com"
        mock_user.name = "New User"
        mock_user.age = 25
        mock_user.welcome_email_sent = False
        
        # Make refresh populate the user
        def mock_refresh(obj):
            pass
        mock_db.refresh = mock_refresh
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        
        # Patch the UserModel constructor to return our mock
        with patch('app.main.UserModel', return_value=mock_user):
            app.dependency_overrides[get_db] = lambda: mock_db
            
            try:
                response = client.post("/users", json={
                    "email": "newuser@example.com",
                    "name": "New User",
                    "age": 25
                })
                assert response.status_code == 201
                data = response.json()
                assert data["email"] == "newuser@example.com"
                assert data["name"] == "New User"
                assert data["age"] == 25
            finally:
                app.dependency_overrides.clear()
    
    def test_create_user_duplicate_email(self, client, mock_db):
        # Mock existing user
        existing_user = MagicMock(spec=UserModel)
        existing_user.email = "existing@example.com"
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.post("/users", json={
                "email": "existing@example.com",
                "name": "Test User",
                "age": 30
            })
            assert response.status_code == 400
            assert response.json()["detail"] == "Email already registered"
        finally:
            app.dependency_overrides.clear()
    
    def test_delete_user_success(self, client, mock_db):
        # Mock existing user
        mock_user = MagicMock(spec=UserModel)
        mock_user.id = 1
        mock_user.email = "delete@example.com"
        mock_user.name = "Delete User"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db.add = MagicMock()
        mock_db.delete = MagicMock()
        mock_db.commit = MagicMock()
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.delete("/users/1")
            assert response.status_code == 204
            # Verify delete was called
            mock_db.delete.assert_called_once_with(mock_user)
        finally:
            app.dependency_overrides.clear()
    
    def test_delete_user_not_found(self, client, mock_db):
        # Mock user not found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        app.dependency_overrides[get_db] = lambda: mock_db
        
        try:
            response = client.delete("/users/999")
            assert response.status_code == 404
            assert response.json()["detail"] == "User not found"
        finally:
            app.dependency_overrides.clear()
