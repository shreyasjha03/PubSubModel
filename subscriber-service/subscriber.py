import os
from celery import Celery
from kombu import Queue, Exchange
from datetime import datetime
import json
import time
from enum import Enum
from typing import Dict

# Message Types and Priorities (matching publisher)
class MessageType(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    WHATSAPP = "whatsapp"

class MessagePriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

# Fetch environment variables with local fallback
rabbitmq_user = os.getenv('RABBITMQ_USER', 'user')  # Use the same credentials as the publisher
rabbitmq_pass = os.getenv('RABBITMQ_PASS', 'password')
rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabbitmq')

# Broker URL
broker_url = f'amqp://{rabbitmq_user}:{rabbitmq_pass}@{rabbitmq_host}:5672//'

# Initialize Celery
app = Celery('subscriber', broker=broker_url)

# Configure Celery
app.conf.update(
    task_serializer='json',  # Use JSON to handle structured data
    accept_content=['json'],  # Accept only JSON
    result_serializer='json',
    task_queues=(
        # SMS queues with priorities
        Queue(f'sms_{MessagePriority.HIGH}_queue', Exchange('', type='direct'), routing_key=f'sms_{MessagePriority.HIGH}_queue'),
        Queue(f'sms_{MessagePriority.MEDIUM}_queue', Exchange('', type='direct'), routing_key=f'sms_{MessagePriority.MEDIUM}_queue'),
        Queue(f'sms_{MessagePriority.LOW}_queue', Exchange('', type='direct'), routing_key=f'sms_{MessagePriority.LOW}_queue'),
        
        # Email queues with priorities
        Queue(f'email_{MessagePriority.HIGH}_queue', Exchange('', type='direct'), routing_key=f'email_{MessagePriority.HIGH}_queue'),
        Queue(f'email_{MessagePriority.MEDIUM}_queue', Exchange('', type='direct'), routing_key=f'email_{MessagePriority.MEDIUM}_queue'),
        Queue(f'email_{MessagePriority.LOW}_queue', Exchange('', type='direct'), routing_key=f'email_{MessagePriority.LOW}_queue'),
        
        # WhatsApp queues with priorities
        Queue(f'whatsapp_{MessagePriority.HIGH}_queue', Exchange('', type='direct'), routing_key=f'whatsapp_{MessagePriority.HIGH}_queue'),
        Queue(f'whatsapp_{MessagePriority.MEDIUM}_queue', Exchange('', type='direct'), routing_key=f'whatsapp_{MessagePriority.MEDIUM}_queue'),
        Queue(f'whatsapp_{MessagePriority.LOW}_queue', Exchange('', type='direct'), routing_key=f'whatsapp_{MessagePriority.LOW}_queue'),
    ),
    task_default_queue=f'sms_{MessagePriority.MEDIUM}_queue',  # Default queue
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    broker_heartbeat=60,  # Set heartbeat to keep the connection alive
    task_acks_late=True,  # Enable late acknowledgment
    task_reject_on_worker_lost=True  # Reject task if worker is lost
)

def process_message_with_timeout(func):
    def wrapper(self, body):
        try:
            message = body if isinstance(body, dict) else json.loads(body)
            timeout = message.get('timeout', 30)
            start_time = time.time()
            
            # Log received message
            print(f"\n{'='*50}")
            print(f"Received message at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Priority: {message.get('priority', 'MEDIUM')}")
            print(f"Timeout: {timeout} seconds")
            print(f"Retry Count: {message.get('retry_count', 3)}")
            if 'metadata' in message:
                print(f"Metadata: {message['metadata']}")
            
            # Simulate processing based on priority
            process_time = 2 if message.get('priority') == 'HIGH' else 4
            time.sleep(process_time)
            
            # Check timeout
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Message processing exceeded timeout of {timeout} seconds")
            
            # Process the message
            result = func(self, message)
            
            # Log completion
            print(f"Processing completed in {time.time() - start_time:.2f} seconds")
            print(f"{'='*50}\n")
            
            return result
        except Exception as e:
            print(f"Error processing message: {e}")
            print(f"Raw body: {body}")
            raise
    return wrapper

@app.task(name='process_sms_message', bind=True)
@process_message_with_timeout
def process_sms_message(self, message):
    """Process SMS message"""
    args = message.get('args', [{}])[0]
    content = args.get('content', '')
    print(f"\nProcessing SMS Message:")
    print(f"Content: {content}")
    return {"status": "success", "type": "sms"}

@app.task(name='process_email_message', bind=True)
@process_message_with_timeout
def process_email_message(self, message):
    """Process Email message"""
    args = message.get('args', [{}])[0]
    content = args.get('content', '')
    print(f"\nProcessing Email Message:")
    print(f"Content: {content}")
    return {"status": "success", "type": "email"}

@app.task(name='process_whatsapp_message', bind=True)
@process_message_with_timeout
def process_whatsapp_message(self, message):
    """Process WhatsApp message"""
    args = message.get('args', [{}])[0]
    content = args.get('content', '')
    print(f"\nProcessing WhatsApp Message:")
    print(f"Content: {content}")
    return {"status": "success", "type": "whatsapp"}

if __name__ == '__main__':
    print(f"Starting Celery worker for RabbitMQ at {rabbitmq_host}")
    app.worker_main(['worker', '--loglevel=INFO'])
