import pika
import json
import logging
import time
from app.rabbitmq import get_rabbitmq_connection
from app.email import send_welcome_email, send_goodbye_email
from app.database import SessionLocal
from app.models import Notification

logger = logging.getLogger(__name__)


# gets called whenever we receive a message from rabbitmq
def callback(ch, method, properties, body):
    try:
        # parse json from message body
        event = json.loads(body)
        event_type = event.get('type')
        email = event.get('email')
        name = event.get('name')
        
        logger.info(f"Received event: {event_type} for {email}")
        
        # figure out which email to send
        if event_type == 'user.created':
            send_welcome_email(email, name)
        elif event_type == 'user.deleted':
            send_goodbye_email(email, name)
        else:
            logger.warning(f"Unknown event type: {event_type}")
        
        # tell rabbitmq we're done with this message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        # don't retry if it failed, just drop it
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


# start listening for messages on the queue with retry logic
def start_consumer():
    logger.info("Starting RabbitMQ consumer...")
    
    max_retries = 10
    retry_delay = 2  # start with 2 seconds
    max_retry_delay = 60  # cap at 60 seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to RabbitMQ (attempt {attempt + 1}/{max_retries})...")
            connection = get_rabbitmq_connection()
            
            if not connection:
                if attempt < max_retries - 1:
                    logger.warning(f"Could not connect to RabbitMQ, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, max_retry_delay)  # exponential backoff
                    continue
                else:
                    logger.error("Could not connect to RabbitMQ after all retries, consumer not started")
                    return
            
            channel = connection.channel()
            
            # make sure queue exists (durable = survives restarts)
            channel.queue_declare(queue='notification_queue', durable=True)
            
            # don't grab more than 1 message at a time
            channel.basic_qos(prefetch_count=1)
            
            # start listening
            channel.basic_consume(
                queue='notification_queue',
                on_message_callback=callback
            )
            
            logger.info("Successfully connected! Waiting for messages in notification_queue...")
            channel.start_consuming()
            
            # if we get here, connection was closed - try to reconnect
            logger.warning("RabbitMQ connection closed, attempting to reconnect...")
            time.sleep(5)
            
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
            break
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)
            else:
                logger.error("Max retries reached, consumer stopped")
                break
