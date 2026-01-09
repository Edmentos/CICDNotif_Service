import pytest
from unittest.mock import patch, MagicMock, Mock, call
import smtplib
import os
from email.message import EmailMessage


class TestWelcomeEmail:
    """Test send_welcome_email function"""
    
    def test_welcome_email_no_smtp_configured(self):
        """Test that email is skipped when SMTP not configured"""
        with patch.dict('os.environ', {}, clear=True):
            from app.email import send_welcome_email
            
            # Should not raise exception, just log and return
            send_welcome_email("test@example.com", "Test User")
    
    @patch.dict('os.environ', {
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_PORT': '465',
        'SMTP_USER': 'user@example.com',
        'SMTP_PASSWORD': 'password',
        'SMTP_USE_SSL': 'true'
    })
    @patch('app.email.smtplib.SMTP_SSL')
    @patch('app.email.SessionLocal')
    def test_welcome_email_ssl_success(self, mock_session_local, mock_smtp_ssl):
        """Test successful welcome email with SSL"""
        from app.email import send_welcome_email
        
        # Mock SMTP
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = mock_smtp
        
        # Mock database
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        send_welcome_email("test@example.com", "Test User")
        
        # Verify SMTP was called
        mock_smtp.login.assert_called_once_with('user@example.com', 'password')
        mock_smtp.send_message.assert_called_once()
        
        # Verify notification saved to DB
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @patch.dict('os.environ', {
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_PORT': '587',
        'SMTP_USER': 'user@example.com',
        'SMTP_PASSWORD': 'password',
        'SMTP_USE_SSL': 'false',
        'SMTP_STARTTLS': 'true'
    })
    @patch('app.email.smtplib.SMTP')
    @patch('app.email.SessionLocal')
    def test_welcome_email_starttls_success(self, mock_session_local, mock_smtp):
        """Test successful welcome email with STARTTLS"""
        from app.email import send_welcome_email
        
        # Mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Mock database
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        send_welcome_email("test@example.com", "Test User")
        
        # Verify STARTTLS was called
        mock_server.ehlo.assert_called()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
    
    @patch.dict('os.environ', {
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_PORT': '25',
        'SMTP_USE_SSL': 'false',
        'SMTP_STARTTLS': 'false',
        'SMTP_USER': '',
        'SMTP_PASSWORD': ''
    })
    @patch('app.email.smtplib.SMTP')
    @patch('app.email.SessionLocal')
    def test_welcome_email_no_auth(self, mock_session_local, mock_smtp):
        """Test email without authentication"""
        from app.email import send_welcome_email
        
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        send_welcome_email("test@example.com", "Test User")
        
        # Verify login was NOT called (no credentials)
        mock_server.login.assert_not_called()
        mock_server.send_message.assert_called_once()
    
    @patch.dict('os.environ', {
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_FROM': 'custom@example.com',
        'SMTP_USE_SSL': 'true'
    })
    @patch('app.email.smtplib.SMTP_SSL')
    @patch('app.email.SessionLocal')
    def test_welcome_email_custom_from(self, mock_session_local, mock_smtp_ssl):
        """Test email with custom FROM address"""
        from app.email import send_welcome_email
        
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = mock_smtp
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        send_welcome_email("test@example.com", "Test User")
        
        # Check that message was sent
        assert mock_smtp.send_message.called
        msg = mock_smtp.send_message.call_args[0][0]
        assert msg["From"] == "custom@example.com"
    
    @patch.dict('os.environ', {
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_USE_SSL': 'true'
    })
    @patch('app.email.smtplib.SMTP_SSL')
    @patch('app.email.SessionLocal')
    def test_welcome_email_smtp_failure(self, mock_session_local, mock_smtp_ssl):
        """Test handling of SMTP failure"""
        from app.email import send_welcome_email
        
        # Mock SMTP to raise exception
        mock_smtp = MagicMock()
        mock_smtp.send_message.side_effect = Exception("SMTP Error")
        mock_smtp_ssl.return_value.__enter__.return_value = mock_smtp
        
        # Mock database
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        send_welcome_email("test@example.com", "Test User")
        
        # Verify failed notification was saved
        assert mock_db.add.called
        notification = mock_db.add.call_args[0][0]
        assert notification.delivered == False
    
    @patch.dict('os.environ', {
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_USE_SSL': 'true'
    })
    @patch('app.email.smtplib.SMTP_SSL')
    @patch('app.email.SessionLocal')
    def test_welcome_email_db_save_failure(self, mock_session_local, mock_smtp_ssl):
        """Test handling of database save failure"""
        from app.email import send_welcome_email
        
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = mock_smtp
        
        # Mock database to raise exception on commit
        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("DB Error")
        mock_session_local.return_value = mock_db
        
        # Should not raise exception
        send_welcome_email("test@example.com", "Test User")
        
        # Verify close was called despite error
        mock_db.close.assert_called()


class TestGoodbyeEmail:
    """Test send_goodbye_email function"""
    
    def test_goodbye_email_no_smtp_configured(self):
        """Test that email is skipped when SMTP not configured"""
        with patch.dict('os.environ', {}, clear=True):
            from app.email import send_goodbye_email
            
            # Should not raise exception
            send_goodbye_email("test@example.com", "Test User")
    
    @patch.dict('os.environ', {
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_PORT': '465',
        'SMTP_USER': 'user@example.com',
        'SMTP_PASSWORD': 'password',
        'SMTP_USE_SSL': 'true'
    })
    @patch('app.email.smtplib.SMTP_SSL')
    @patch('app.email.SessionLocal')
    def test_goodbye_email_ssl_success(self, mock_session_local, mock_smtp_ssl):
        """Test successful goodbye email with SSL"""
        from app.email import send_goodbye_email
        
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = mock_smtp
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        send_goodbye_email("test@example.com", "Test User")
        
        # Verify SMTP was called
        mock_smtp.login.assert_called_once()
        mock_smtp.send_message.assert_called_once()
        
        # Verify notification saved
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @patch.dict('os.environ', {
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_PORT': '587',
        'SMTP_USE_SSL': 'false',
        'SMTP_STARTTLS': 'true'
    })
    @patch('app.email.smtplib.SMTP')
    @patch('app.email.SessionLocal')
    def test_goodbye_email_starttls(self, mock_session_local, mock_smtp):
        """Test goodbye email with STARTTLS"""
        from app.email import send_goodbye_email
        
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        send_goodbye_email("test@example.com", "Test User")
        
        # Verify STARTTLS flow
        mock_server.ehlo.assert_called()
        mock_server.starttls.assert_called_once()
        mock_server.send_message.assert_called_once()
    
    @patch.dict('os.environ', {
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_USE_SSL': 'true'
    })
    @patch('app.email.smtplib.SMTP_SSL')
    @patch('app.email.SessionLocal')
    def test_goodbye_email_smtp_failure(self, mock_session_local, mock_smtp_ssl):
        """Test handling of SMTP failure for goodbye email"""
        from app.email import send_goodbye_email
        
        mock_smtp = MagicMock()
        mock_smtp.send_message.side_effect = Exception("SMTP Error")
        mock_smtp_ssl.return_value.__enter__.return_value = mock_smtp
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        send_goodbye_email("test@example.com", "Test User")
        
        # Verify failed notification was saved
        notification = mock_db.add.call_args[0][0]
        assert notification.delivered == False
        assert notification.notification_type == "goodbye"
    
    @patch.dict('os.environ', {
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_USE_SSL': 'false'
    })
    @patch('app.email.smtplib.SMTP')
    @patch('app.email.SessionLocal')
    def test_goodbye_email_no_starttls(self, mock_session_local, mock_smtp):
        """Test goodbye email without STARTTLS"""
        from app.email import send_goodbye_email
        
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        send_goodbye_email("test@example.com", "Test User")
        
        # Verify starttls was NOT called
        mock_server.starttls.assert_not_called()
        mock_server.send_message.assert_called_once()
    
    @patch.dict('os.environ', {
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_PORT': '25',
        'SMTP_USE_SSL': 'false',
        'SMTP_USER': '',
        'SMTP_PASSWORD': ''
    })
    @patch('app.email.smtplib.SMTP')
    @patch('app.email.SessionLocal')
    def test_goodbye_email_no_auth(self, mock_session_local, mock_smtp):
        """Test goodbye email without authentication"""
        from app.email import send_goodbye_email
        
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        send_goodbye_email("test@example.com", "Test User")
        
        # No login should be called
        mock_server.login.assert_not_called()
        mock_server.send_message.assert_called_once()
    
    @patch.dict('os.environ', {
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_FROM': 'goodbye@example.com',
        'SMTP_USE_SSL': 'true'
    })
    @patch('app.email.smtplib.SMTP_SSL')
    @patch('app.email.SessionLocal')
    def test_goodbye_email_custom_from(self, mock_session_local, mock_smtp_ssl):
        """Test goodbye email with custom FROM address"""
        from app.email import send_goodbye_email
        
        mock_smtp = MagicMock()
        mock_smtp_ssl.return_value.__enter__.return_value = mock_smtp
        
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        send_goodbye_email("test@example.com", "Test User")
        
        # Verify message was sent
        assert mock_smtp.send_message.called
        msg = mock_smtp.send_message.call_args[0][0]
        assert msg["From"] == "goodbye@example.com"
        assert "feedback" in msg.get_content().lower() or "survey" in msg.get_content().lower()
