import pika
import json
import logging
from app.rabbitmq import get_rabbitmq_connection
from app.email import send_welcome_email, send_goodbye_email
from app.database import SessionLocal
from app.models import Notification

logger = logging.getLogger(__name__)


# This runs when we receive a message from RabbitMQ
def callback(ch, method, properties, body):
    try:
        # Parse the JSON message
        event = json.loads(body)
        event_type = event.get('type')
        email = event.get('email')
        name = event.get('name')
        
        logger.info(f"Received event: {event_type} for {email}")
        
        # Send the right email based on event type
        if event_type == 'user.created':
            send_welcome_email(email, name)
        elif event_type == 'user.deleted':
            send_goodbye_email(email, name)
        else:
            logger.warning(f"Unknown event type: {event_type}")
        
        # Tell RabbitMQ we processed the message successfully
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        # Don't requeue the message if it failed - send to dead letter queue instead
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


# Starts listening to the notification queue
def start_consumer():
    logger.info("Starting RabbitMQ consumer...")
    
    try:
        connection = get_rabbitmq_connection()
        if not connection:
            logger.error("Could not connect to RabbitMQ, consumer not started")
            return
            
        channel = connection.channel()
        
        # Make sure the queue exists and will survive server restarts
        channel.queue_declare(queue='notification_queue', durable=True)
        
        # Only process one message at a time
        channel.basic_qos(prefetch_count=1)
        
        # Start consuming messages
        channel.basic_consume(
            queue='notification_queue',
            on_message_callback=callback
        )
        
        logger.info("Waiting for messages in notification_queue...")
        channel.start_consuming()
        
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as e:
        logger.error(f"Consumer error: {e}")
