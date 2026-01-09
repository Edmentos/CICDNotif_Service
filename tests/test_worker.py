import pytest
from unittest.mock import patch, MagicMock, Mock
import json


class TestWorkerCallback:
    """Test RabbitMQ message callback function"""
    
    @patch('app.worker.send_welcome_email')
    def test_callback_user_created(self, mock_send_welcome):
        """Test callback for user.created event"""
        from app.worker import callback
        
        # Mock channel and method
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 'test-tag-123'
        
        # Create event message
        event = {
            'type': 'user.created',
            'email': 'newuser@example.com',
            'name': 'New User'
        }
        body = json.dumps(event).encode()
        
        callback(mock_ch, mock_method, None, body)
        
        # Verify welcome email was sent
        mock_send_welcome.assert_called_once_with('newuser@example.com', 'New User')
        
        # Verify message was acknowledged
        mock_ch.basic_ack.assert_called_once_with(delivery_tag='test-tag-123')
    
    @patch('app.worker.send_goodbye_email')
    def test_callback_user_deleted(self, mock_send_goodbye):
        """Test callback for user.deleted event"""
        from app.worker import callback
        
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 'test-tag-456'
        
        event = {
            'type': 'user.deleted',
            'email': 'deleted@example.com',
            'name': 'Deleted User'
        }
        body = json.dumps(event).encode()
        
        callback(mock_ch, mock_method, None, body)
        
        # Verify goodbye email was sent
        mock_send_goodbye.assert_called_once_with('deleted@example.com', 'Deleted User')
        
        # Verify acknowledgment
        mock_ch.basic_ack.assert_called_once_with(delivery_tag='test-tag-456')
    
    def test_callback_unknown_event_type(self):
        """Test callback with unknown event type"""
        from app.worker import callback
        
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 'test-tag-789'
        
        event = {
            'type': 'unknown.event',
            'email': 'test@example.com',
            'name': 'Test User'
        }
        body = json.dumps(event).encode()
        
        callback(mock_ch, mock_method, None, body)
        
        # Should still acknowledge even with unknown type
        mock_ch.basic_ack.assert_called_once_with(delivery_tag='test-tag-789')
    
    def test_callback_invalid_json(self):
        """Test callback with invalid JSON"""
        from app.worker import callback
        
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 'test-tag-error'
        
        body = b'invalid json {'
        
        callback(mock_ch, mock_method, None, body)
        
        # Should send negative acknowledgment
        mock_ch.basic_nack.assert_called_once_with(
            delivery_tag='test-tag-error',
            requeue=False
        )
    
    @patch('app.worker.send_welcome_email')
    def test_callback_send_email_error(self, mock_send_welcome):
        """Test callback when email sending fails"""
        from app.worker import callback
        
        # Make send_welcome_email raise exception
        mock_send_welcome.side_effect = Exception("Email send failed")
        
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 'test-tag-fail'
        
        event = {
            'type': 'user.created',
            'email': 'test@example.com',
            'name': 'Test User'
        }
        body = json.dumps(event).encode()
        
        callback(mock_ch, mock_method, None, body)
        
        # Should send negative acknowledgment without requeue
        mock_ch.basic_nack.assert_called_once_with(
            delivery_tag='test-tag-fail',
            requeue=False
        )
    
    @patch('app.worker.send_welcome_email')
    def test_callback_missing_name_field(self, mock_send_welcome):
        """Test callback with missing name field"""
        from app.worker import callback
        
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 'test-tag-incomplete'
        
        # Event missing 'name' field
        event = {
            'type': 'user.created',
            'email': 'test@example.com'
        }
        body = json.dumps(event).encode()
        
        callback(mock_ch, mock_method, None, body)
        
        # Should call send_welcome_email with None for name
        mock_send_welcome.assert_called_once_with('test@example.com', None)
        # Should still acknowledge
        mock_ch.basic_ack.assert_called_once_with(delivery_tag='test-tag-incomplete')


class TestStartConsumer:
    """Test start_consumer function"""
    
    @patch('app.worker.time.sleep')
    @patch('app.worker.get_rabbitmq_connection')
    def test_start_consumer_no_connection(self, mock_get_conn, mock_sleep):
        """Test start_consumer when connection fails"""
        from app.worker import start_consumer
        
        mock_get_conn.return_value = None
        
        # Should return without error after max retries
        start_consumer()
        
        # Should attempt connection 10 times (max_retries)
        assert mock_get_conn.call_count == 10
    
    @patch('app.worker.time.sleep')
    @patch('app.worker.get_rabbitmq_connection')
    def test_start_consumer_success(self, mock_get_conn, mock_sleep):
        """Test successful consumer start"""
        from app.worker import start_consumer
        
        # Mock connection and channel
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_conn.channel.return_value = mock_channel
        mock_get_conn.return_value = mock_conn
        
        # Make start_consuming raise KeyboardInterrupt to exit loop
        mock_channel.start_consuming.side_effect = KeyboardInterrupt()
        
        start_consumer()
        
        # Verify queue was declared
        mock_channel.queue_declare.assert_called_once_with(
            queue='notification_queue',
            durable=True
        )
        
        # Verify QoS was set
        mock_channel.basic_qos.assert_called_once_with(prefetch_count=1)
        
        # Verify consumer was set up
        mock_channel.basic_consume.assert_called_once()
        
        # Verify consuming started
        mock_channel.start_consuming.assert_called_once()
    
    @patch('app.worker.time.sleep')
    @patch('app.worker.get_rabbitmq_connection')
    def test_start_consumer_keyboard_interrupt(self, mock_get_conn, mock_sleep):
        """Test consumer handling KeyboardInterrupt"""
        from app.worker import start_consumer
        
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_conn.channel.return_value = mock_channel
        mock_get_conn.return_value = mock_conn
        
        # Simulate user interrupt
        mock_channel.start_consuming.side_effect = KeyboardInterrupt()
        
        # Should exit gracefully
        start_consumer()
        
        mock_channel.start_consuming.assert_called_once()
    
    @patch('app.worker.time.sleep')
    @patch('app.worker.get_rabbitmq_connection')
    def test_start_consumer_exception(self, mock_get_conn, mock_sleep):
        """Test consumer handling general exception"""
        from app.worker import start_consumer
        
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_conn.channel.return_value = mock_channel
        mock_get_conn.return_value = mock_conn
        
        # Simulate error during consuming
        mock_channel.start_consuming.side_effect = Exception("Consumer error")
        
        # Should handle exception gracefully
        start_consumer()
        
        # Should try 10 times before giving up
        assert mock_channel.start_consuming.call_count == 10
    
    @patch('app.worker.time.sleep')
    @patch('app.worker.get_rabbitmq_connection')
    def test_start_consumer_callback_registration(self, mock_get_conn, mock_sleep):
        """Test that callback is properly registered"""
        from app.worker import start_consumer, callback
        
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_conn.channel.return_value = mock_channel
        mock_get_conn.return_value = mock_conn
        
        mock_channel.start_consuming.side_effect = KeyboardInterrupt()
        
        start_consumer()
        
        # Verify callback was registered
        call_args = mock_channel.basic_consume.call_args
        assert call_args[1]['queue'] == 'notification_queue'
        assert call_args[1]['on_message_callback'] == callback
    
    @patch('app.worker.time.sleep')
    @patch('app.worker.get_rabbitmq_connection')
    def test_start_consumer_channel_setup(self, mock_get_conn, mock_sleep):
        """Test that channel is properly configured"""
        from app.worker import start_consumer
        
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_conn.channel.return_value = mock_channel
        mock_get_conn.return_value = mock_conn
        
        mock_channel.start_consuming.side_effect = KeyboardInterrupt()
        
        start_consumer()
        
        # Verify channel was created
        mock_conn.channel.assert_called_once()
        
        # Verify durable queue
        queue_declare_call = mock_channel.queue_declare.call_args
        assert queue_declare_call[1]['durable'] == True
