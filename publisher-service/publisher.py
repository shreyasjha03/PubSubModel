import os
import pika
import json
import uuid
import logging
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, Dict
from enum import Enum
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI application starting up...")

@app.get("/")
async def root():
    return {"status": "alive"}

# Environment variables
rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
rabbitmq_user = os.getenv("RABBITMQ_USER", "user")
rabbitmq_pass = os.getenv("RABBITMQ_PASS", "password")

class MessageType(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    WHATSAPP = "whatsapp"

class MessagePriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Message(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)
    timeout: int = Field(default=30, ge=1, le=300)
    priority: MessagePriority = Field(default=MessagePriority.MEDIUM)
    metadata: Dict = Field(default_factory=dict)

    def determine_type(self) -> MessageType:
        # Email patterns
        email_patterns = [
            r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}',  # Email address
            r'subject:.*|subject .*|re:.*',  # Subject line
            r'dear.*|hi.*|hello.*',  # Email greetings
            r'find attached|please find|attached|report'  # Email content indicators
        ]

        # WhatsApp patterns
        whatsapp_patterns = [
            r'whatsapp:.*|wa:.*',  # WhatsApp indicators
            r'sent via whatsapp',
            r'message me on.*',
            r'chat.*with.*'
        ]

        # SMS patterns
        sms_patterns = [
            r'^\+\d{10,}',  # Phone number at start
            r'SMS:.*|txt:.*',  # SMS indicators
            r'^\d{6}$',  # OTP-like numbers
            r'text.*to.*'  # Text message indicators
        ]

        content = self.content.lower()

        # Check for email patterns
        for pattern in email_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return MessageType.EMAIL

        # Check for WhatsApp patterns
        for pattern in whatsapp_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return MessageType.WHATSAPP

        # Check for SMS patterns
        for pattern in sms_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return MessageType.SMS

        # Default to SMS if no specific pattern is matched
        return MessageType.SMS

    def get_queue_name(self) -> str:
        return f"{self.determine_type()}_{self.priority}_queue"

    def get_message_info(self) -> Dict:
        msg_type = self.determine_type()
        return {
            "type": msg_type,
            "priority": self.priority,
            "content_length": len(self.content),
            "timeout": self.timeout,
            "content_preview": self.content[:50] + "..." if len(self.content) > 50 else self.content
        }

# Pika connection setup
def get_rabbitmq_channel():
    try:
        credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=rabbitmq_host, credentials=credentials)
        )
        channel = connection.channel()
        # Declare queues for different message types
        for queue in ["sms_queue", "email_queue", "whatsapp_queue"]:
            channel.queue_declare(queue=queue, durable=True)
        return channel
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RabbitMQ connection error: {e}")

@app.post("/publish")
def publish_message(message: Message):
    try:
        message_type = message.determine_type()
        queue_name = message.get_queue_name()
        message_info = message.get_message_info()
        
        channel = get_rabbitmq_channel()
        task_message = {
            "task": f"process_{message_type}_message",
            "id": str(uuid.uuid4()),
            "args": [{"content": message.content}],
            "kwargs": {},
            "timeout": message.timeout,
            "priority": message.priority,
            "metadata": message.metadata
        }

        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(task_message),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
                content_encoding="utf-8",
                expiration=str(message.timeout * 1000),
                priority=get_priority_value(message.priority)
            ),
        )
        logger.info(f"Published message: {message_info}")
        return {
            "message": f"{message_type} message published successfully",
            "queue": queue_name,
            "info": message_info
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to publish message: {e}")
    finally:
        if channel:
            channel.close()

def get_priority_value(priority: MessagePriority) -> int:
    priority_map = {
        MessagePriority.HIGH: 3,
        MessagePriority.MEDIUM: 2,
        MessagePriority.LOW: 1
    }
    return priority_map.get(priority, 2)

if __name__ == "__main__":
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
