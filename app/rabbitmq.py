import pika
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Circuit breaker for RabbitMQ
_rabbitmq_circuit_breaker = {
    'failures': 0,
    'last_failure_time': None,
    'state': 'closed',  # closed, open, half_open
    'failure_threshold': 3,
    'timeout': 30  # seconds before trying again
}

def _check_rabbitmq_circuit():
    """Check if circuit breaker allows RabbitMQ operations"""
    cb = _rabbitmq_circuit_breaker
    
    if cb['state'] == 'open':
        if cb['last_failure_time'] and \
           (datetime.now() - cb['last_failure_time']).total_seconds() > cb['timeout']:
            cb['state'] = 'half_open'
            logger.info("RabbitMQ circuit breaker entering half-open state")
            return True
        return False
    
    return True

def _record_rabbitmq_success():
    """Record successful RabbitMQ operation"""
    cb = _rabbitmq_circuit_breaker
    if cb['state'] == 'half_open':
        logger.info("RabbitMQ circuit breaker closing after successful operation")
    cb['failures'] = 0
    cb['state'] = 'closed'
    cb['last_failure_time'] = None

def _record_rabbitmq_failure():
    """Record failed RabbitMQ operation"""
    cb = _rabbitmq_circuit_breaker
    cb['failures'] += 1
    cb['last_failure_time'] = datetime.now()
    
    if cb['failures'] >= cb['failure_threshold']:
        if cb['state'] != 'open':
            logger.warning(f"RabbitMQ circuit breaker opened after {cb['failures']} failures")
        cb['state'] = 'open'


# Connects to RabbitMQ server using URL or individual credentials
def get_rabbitmq_connection():
    # Check circuit breaker
    if not _check_rabbitmq_circuit():
        logger.warning("RabbitMQ circuit breaker is open; connection attempt blocked")
        return None
    
    try:
        # Try using connection URL first (cleaner)
        rabbitmq_url = os.getenv('RABBITMQ_URL')
        
        if rabbitmq_url:
            parameters = pika.URLParameters(rabbitmq_url)
            parameters.heartbeat = 600
            parameters.blocked_connection_timeout = 300
            connection = pika.BlockingConnection(parameters)
            logger.info(f"Connected to RabbitMQ using URL")
            _record_rabbitmq_success()
            return connection
        
        # Fall back to individual parameters
        credentials = pika.PlainCredentials(
            os.getenv('RABBITMQ_USER', 'guest'),
            os.getenv('RABBITMQ_PASSWORD', 'guest')
        )
        parameters = pika.ConnectionParameters(
            host=os.getenv('RABBITMQ_HOST', 'localhost'),
            port=int(os.getenv('RABBITMQ_PORT', 5672)),
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        connection = pika.BlockingConnection(parameters)
        logger.info(f"Connected to RabbitMQ at {os.getenv('RABBITMQ_HOST', 'localhost')}")
        _record_rabbitmq_success()
        return connection
        
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        _record_rabbitmq_failure()
        return None


# Checks if we can connect to RabbitMQ
def check_rabbitmq_connection():
    try:
        connection = get_rabbitmq_connection()
        if connection:
            connection.close()
            return True
        return False
    except:
        return False
