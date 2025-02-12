import os
import json
import logging
from celery import Celery, Task
from kombu import Queue, Exchange
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from celery.signals import celeryd_after_setup
from twilio.rest import Client

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add this after logging config
logging.getLogger('amqp').setLevel(logging.DEBUG)
logging.getLogger('celery').setLevel(logging.DEBUG)
logging.getLogger('celery.worker').setLevel(logging.DEBUG)
logging.getLogger('celery.app.trace').setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# Celery configuration
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
BROKER_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:5672/"

# Configure queues - consistent settings
task_queues = [
    Queue('sms_queue', 
          Exchange('sms_queue', type='direct', durable=True, auto_delete=True),
          routing_key='sms_queue',
          durable=True,
          auto_delete=True),
    Queue('email_queue',
          Exchange('email_queue', type='direct', durable=True, auto_delete=True),
          routing_key='email_queue',
          durable=True,
          auto_delete=True),
    Queue('whatsapp_queue',
          Exchange('whatsapp_queue', type='direct', durable=True, auto_delete=True),
          routing_key='whatsapp_queue',
          durable=True,
          auto_delete=True)
]

app = Celery('subscriber',
             broker=BROKER_URL)

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_queues=task_queues,
    task_routes={
        'process_sms_message': {
            'queue': 'sms_queue',
            'exchange': 'sms_queue',
            'routing_key': 'sms_queue'
        },
        'process_email_message': {
            'queue': 'email_queue',
            'exchange': 'email_queue',
            'routing_key': 'email_queue'
        },
        'process_whatsapp_message': {
            'queue': 'whatsapp_queue',
            'exchange': 'whatsapp_queue',
            'routing_key': 'whatsapp_queue'
        }
    },
    task_default_queue='default',
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=None,  # Keep retrying forever
    worker_lost_wait=30.0,  # Wait 30 seconds before marking task as lost
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_cancel_long_running_tasks_on_connection_loss=False,  # Don't cancel tasks on connection loss
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s',
    task_track_started=True,
    task_ignore_result=False,
    task_store_errors_even_if_ignored=True,
    worker_send_task_events=True,
    task_send_sent_event=True
)

# Set up Jinja2 environment
TEMPLATE_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=True
)

# Add Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'key')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'key')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', 'key')

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

class MessageProcessor:
    @staticmethod
    def get_template_path(request_type: str, channel: str) -> str:
        """Get the full path to template file"""
        template_dir = Path(__file__).parent / "templates"
        if channel == 'email':
            return template_dir / channel / f"{request_type}.html"
        else:
            return template_dir / channel / f"{request_type}.txt"

    @staticmethod
    def read_template(template_path: Path) -> str:
        """Read template file contents"""
        try:
            with open(template_path, 'r') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading template {template_path}: {str(e)}")
            raise

# Define base task
class MessageTask(Task):
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f'Task failed: {task_id}')
        logger.error(f'Error: {exc}')
        super().on_failure(exc, task_id, args, kwargs, einfo)

@app.task(
    bind=True,
    base=MessageTask,
    name='process_sms_message',
    queue='sms_queue',
    autoretry_for=(Exception,),
    max_retries=3,
    acks_late=True
)
def process_sms_message(self, message_data):
    """Process SMS messages"""
    try:
        logger.info("\n==================================================")
        logger.info("📱 Processing SMS Message")
        logger.info("--------------------------------------------------")
        logger.info(f"Task ID: {self.request.id}")
        
        # Get recipient phone number
        to_number = message_data.get('content', {}).get('phone')
        name = message_data.get('content', {}).get('name')
        if not to_number:
            raise ValueError("No phone number provided")

        # Get template and render message
        template_path = MessageProcessor.get_template_path(
            message_data['request_type'].lower(),
            'sms'
        )
        template = MessageProcessor.read_template(template_path)
        
        try:
            # Send SMS via Twilio
            message = twilio_client.messages.create(
                body=template,
                from_="+19284370633",
                to=to_number,
            )
            
            logger.info(f"✅ SMS sent successfully! SID: {message.sid}")
            logger.info(f"📱 To: {to_number}")
            logger.info(f"💬 Message: {template}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send SMS: {str(e)}")
            raise

        return {
            'status': 'success',
            'channel': 'sms',
            'task_id': self.request.id,
            'request_id': message_data.get('request_id'),
            'twilio_message_sid': message.sid,
            'recipient': to_number
        }
    except Exception as e:
        logger.error(f"Error processing SMS message: {str(e)}")
        raise

@app.task(bind=True, base=MessageTask, name='process_email_message')
def process_email_message(self, message_data):
    """Process Email messages"""
    try:
        logger.info("\n==================================================")
        logger.info("📧 Processing Email Message")
        logger.info("--------------------------------------------------")
        logger.info(f"Task ID: {self.request.id}")
        
        # Get template path and render template
        template_path = MessageProcessor.get_template_path(
            message_data['request_type'].lower(),
            'email'
        )
        
        # Load and render template with Jinja2
        template = jinja_env.get_template(f"email/{message_data['request_type'].lower()}.html")
        rendered_content = template.render(
            content=message_data.get('content', {}),
            metadata=message_data.get('meta_data', {}),
            request_id=message_data.get('request_id'),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # Log email preview
        logger.info("\n📧 Email Preview:")
        logger.info("--------------------------------------------------")
        logger.info(f"To: {message_data.get('content', {}).get('email')}")
        logger.info(f"Subject: Welcome to Our Service!")
        logger.info("Body:")
        logger.info(f"Dear {message_data.get('content', {}).get('name')},")
        logger.info("Your account has been successfully created.")
        logger.info(f"Email: {message_data.get('content', {}).get('email')}")
        logger.info("Click the 'Get Started' button to begin exploring our services.")
        logger.info("--------------------------------------------------")
        logger.info(f"Request ID: {message_data.get('request_id')}")
        logger.info("==================================================\n")
        
        return {
            'status': 'success',
            'channel': 'email',
            'task_id': self.request.id,
            'request_id': message_data.get('request_id'),
            'recipient': message_data.get('content', {}).get('email'),
            'rendered_content': rendered_content
        }
    except Exception as e:
        logger.error(f"Error processing email message: {str(e)}")
        logger.exception("Full traceback:")
        raise

@app.task(bind=True, base=MessageTask, name='process_whatsapp_message')
def process_whatsapp_message(self, message_data):
    """Process WhatsApp messages"""
    try:
        logger.info("\n==================================================")
        logger.info("💬 Processing WhatsApp Message")
        logger.info("--------------------------------------------------")
        logger.info(f"Task ID: {self.request.id}")
        logger.info(f"Message Content: {message_data.get('content', 'No content')}")
        logger.info(f"Request ID: {message_data.get('request_id', 'No request ID')}")
        logger.info(f"Template ID: {message_data.get('template_id', 'No template ID')}")
        logger.info(f"Metadata: {message_data.get('meta_data', {})}")
        logger.info("==================================================\n")
        
        return {
            'status': 'success',
            'channel': 'whatsapp',
            'task_id': self.request.id,
            'request_id': message_data.get('request_id')
        }
    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {str(e)}")
        raise

# Register tasks
app.tasks.register(process_sms_message)
app.tasks.register(process_email_message)
app.tasks.register(process_whatsapp_message)

# Add this function to check queue bindings
@app.task
def check_queues():
    logger.info("Checking queue bindings...")
    try:
        with app.pool.acquire(block=True) as conn:
            channel = conn.channel()
            
            # Check each queue
            for queue_name in ['sms_queue', 'email_queue', 'whatsapp_queue']:
                try:
                    queue = channel.queue_declare(queue=queue_name, passive=True)
                    logger.info(f"Queue '{queue_name}' exists with {queue.method.message_count} messages")
                except Exception as e:
                    logger.error(f"Queue '{queue_name}' check failed: {str(e)}")
    except Exception as e:
        logger.error(f"Queue check failed: {str(e)}")

# After creating Celery app
def setup_queues():
    logger.info("Setting up queue bindings...")
    with app.pool.acquire(block=True) as conn:
        channel = conn.channel()
        
        # Declare exchanges and queues
        for queue_name in ['sms_queue', 'email_queue', 'whatsapp_queue']:
            exchange = Exchange(queue_name, type='direct', durable=True)
            queue = Queue(
                queue_name,
                exchange=exchange,
                routing_key=queue_name,
                durable=True
            )
            queue(channel).declare()
            logger.info(f"✅ Declared queue and exchange: {queue_name}")

# Add this check at startup
def check_templates():
    logger.info("Checking templates...")
    template_dir = Path(__file__).parent / "templates"
    
    for channel in ['email', 'sms']:
        channel_dir = template_dir / channel
        if not channel_dir.exists():
            logger.error(f"❌ Template directory missing: {channel_dir}")
            channel_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Created directory: {channel_dir}")
        
        template_file = channel_dir / "registration_success.txt" if channel == 'sms' else channel_dir / "registration_success.html"
        if not template_file.exists():
            logger.error(f"❌ Template file missing: {template_file}")
            # Create default template
            if channel == 'sms':
                template_file.write_text("Welcome to our service! Your account is ready.")
            else:
                template_file.write_text("<h1>Welcome!</h1><p>Your account has been created successfully.</p>")
            logger.info(f"✅ Created template: {template_file}")

@celeryd_after_setup.connect
def setup_direct_queue(sender, instance, **kwargs):
    """Ensure queues are properly set up after worker initializes"""
    logger.info("Setting up queues after worker initialization...")
    try:
        with app.pool.acquire(block=True) as conn:
            channel = conn.channel()
            
            for queue_name in ['sms_queue', 'email_queue', 'whatsapp_queue']:
                # Declare exchange with matching settings
                channel.exchange_declare(
                    exchange=queue_name,
                    type='direct',
                    durable=True,
                    auto_delete=True
                )
                
                # Declare queue with matching settings
                channel.queue_declare(
                    queue=queue_name,
                    durable=True,
                    auto_delete=True
                )
                
                # Bind queue to exchange
                channel.queue_bind(
                    exchange=queue_name,
                    queue=queue_name,
                    routing_key=queue_name
                )
                logger.info(f"✅ Queue declared: {queue_name}")
    except Exception as e:
        logger.error(f"Error setting up queues: {e}")

if __name__ == '__main__':
    logger.info("Starting Celery worker...")
    check_templates()  # Check templates first
    
    # Start the worker
    app.worker_main([
        'worker',
        '--loglevel=DEBUG',
        '-Q', 'sms_queue,email_queue,whatsapp_queue',
        '-n', 'message_worker@%h',
        '--pool=solo',
        '-c', '1'
    ])
