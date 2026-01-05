import pika
import os
import logging

logger = logging.getLogger(__name__)


# Connects to RabbitMQ server using URL or individual credentials
def get_rabbitmq_connection():
    try:
        # Try using connection URL first (cleaner)
        rabbitmq_url = os.getenv('RABBITMQ_URL')
        
        if rabbitmq_url:
            parameters = pika.URLParameters(rabbitmq_url)
            parameters.heartbeat = 600
            parameters.blocked_connection_timeout = 300
            connection = pika.BlockingConnection(parameters)
            logger.info(f"Connected to RabbitMQ using URL")
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
        return connection
        
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
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
