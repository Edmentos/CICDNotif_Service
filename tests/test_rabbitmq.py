import pytest
from unittest.mock import patch, MagicMock, Mock
import pika
import os


class TestRabbitMQConnection:
    """Test RabbitMQ connection functions"""
    
    @patch.dict('os.environ', {'RABBITMQ_URL': 'amqp://guest:guest@localhost:5672/'})
    @patch('app.rabbitmq.pika.BlockingConnection')
    def test_get_rabbitmq_connection_with_url(self, mock_connection):
        """Test connection using RABBITMQ_URL"""
        from app.rabbitmq import get_rabbitmq_connection
        
        mock_conn = MagicMock()
        mock_connection.return_value = mock_conn
        
        result = get_rabbitmq_connection()
        
        assert result == mock_conn
        mock_connection.assert_called_once()
        # Verify URLParameters was used
        call_args = mock_connection.call_args[0][0]
        assert isinstance(call_args, pika.URLParameters)
    
    @patch.dict('os.environ', {
        'RABBITMQ_USER': 'testuser',
        'RABBITMQ_PASSWORD': 'testpass',
        'RABBITMQ_HOST': 'testhost',
        'RABBITMQ_PORT': '5672'
    }, clear=True)
    @patch('app.rabbitmq.pika.BlockingConnection')
    def test_get_rabbitmq_connection_with_params(self, mock_connection):
        """Test connection using individual parameters"""
        from app.rabbitmq import get_rabbitmq_connection
        
        mock_conn = MagicMock()
        mock_connection.return_value = mock_conn
        
        result = get_rabbitmq_connection()
        
        assert result == mock_conn
        mock_connection.assert_called_once()
        # Verify ConnectionParameters was used
        call_args = mock_connection.call_args[0][0]
        assert isinstance(call_args, pika.ConnectionParameters)
        assert call_args.host == 'testhost'
    
    @patch.dict('os.environ', {}, clear=True)
    @patch('app.rabbitmq.pika.BlockingConnection')
    def test_get_rabbitmq_connection_defaults(self, mock_connection):
        """Test connection with default values"""
        from app.rabbitmq import get_rabbitmq_connection
        
        mock_conn = MagicMock()
        mock_connection.return_value = mock_conn
        
        result = get_rabbitmq_connection()
        
        assert result == mock_conn
        # Verify defaults were used
        call_args = mock_connection.call_args[0][0]
        assert call_args.host == 'localhost'
        assert call_args.port == 5672
    
    @patch('app.rabbitmq.pika.BlockingConnection')
    def test_get_rabbitmq_connection_failure(self, mock_connection):
        """Test connection failure"""
        from app.rabbitmq import get_rabbitmq_connection
        
        mock_connection.side_effect = Exception("Connection failed")
        
        result = get_rabbitmq_connection()
        
        assert result is None
    
    @patch('app.rabbitmq.get_rabbitmq_connection')
    def test_check_rabbitmq_connection_success(self, mock_get_conn):
        """Test successful connection check"""
        from app.rabbitmq import check_rabbitmq_connection
        
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        result = check_rabbitmq_connection()
        
        assert result == True
        mock_conn.close.assert_called_once()
    
    @patch('app.rabbitmq.get_rabbitmq_connection')
    def test_check_rabbitmq_connection_failure(self, mock_get_conn):
        """Test failed connection check"""
        from app.rabbitmq import check_rabbitmq_connection
        
        mock_get_conn.return_value = None
        
        result = check_rabbitmq_connection()
        
        assert result == False
    
    @patch('app.rabbitmq.get_rabbitmq_connection')
    def test_check_rabbitmq_connection_exception(self, mock_get_conn):
        """Test connection check with exception"""
        from app.rabbitmq import check_rabbitmq_connection
        
        mock_get_conn.side_effect = Exception("Connection error")
        
        result = check_rabbitmq_connection()
        
        assert result == False
    
    @patch.dict('os.environ', {
        'RABBITMQ_PORT': '15672',
        'RABBITMQ_HOST': 'localhost'
    }, clear=True)
    @patch('app.rabbitmq.pika.BlockingConnection')
    def test_custom_port(self, mock_connection):
        """Test connection with custom port"""
        from app.rabbitmq import get_rabbitmq_connection
        
        mock_conn = MagicMock()
        mock_connection.return_value = mock_conn
        
        result = get_rabbitmq_connection()
        
        # Since RABBITMQ_URL is not set, it should use individual params
        call_args = mock_connection.call_args[0][0]
        assert call_args.port == 15672
    
    @patch('app.rabbitmq.get_rabbitmq_connection')
    def test_check_connection_closes_on_success(self, mock_get_conn):
        """Test that connection is properly closed after check"""
        from app.rabbitmq import check_rabbitmq_connection
        
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        
        check_rabbitmq_connection()
        
        # Verify close was called
        mock_conn.close.assert_called_once()
