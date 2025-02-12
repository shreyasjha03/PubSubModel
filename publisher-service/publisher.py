import os
import pika
import json
import uuid
import logging
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List
from enum import Enum
import uvicorn
from sqlalchemy.orm import Session
from database import get_db, MessageRequest, MasterTemplate
from sqlalchemy import func
from datetime import datetime
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get RabbitMQ connection details from environment
rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
rabbitmq_user = os.getenv("RABBITMQ_USER", "user")
rabbitmq_pass = os.getenv("RABBITMQ_PASS", "password")

app = FastAPI()

class MessageType(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    WHATSAPP = "whatsapp"

class MessagePriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class MessagePayload(BaseModel):
    request_type: str
    content: Dict
    channels: List[str]
    metadata: Dict = {}

# At the top of the file, add queue settings
QUEUE_SETTINGS = {
    'durable': True,
    'arguments': None
}

@app.post("/publish")
async def publish_message(payload: MessagePayload, db: Session = Depends(get_db)):
    try:
        logger.info(f"\n🚀 Received publish request:")
        logger.info(f"Request Type: {payload.request_type}")
        logger.info(f"Channels: {payload.channels}")
        
        # Create message request record
        message_request = MessageRequest(
            request_type=payload.request_type,
            channels=payload.channels,
            content=payload.content,
            metadata=payload.metadata,
            status='pending'
        )
        db.add(message_request)
        db.commit()
        
        # Initialize RabbitMQ connection
        connection = None
        channel = None
        results = []
        
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            
            # Process each channel
            for channel_name in payload.channels:
                queue_name = f"{channel_name}_queue"
                
                # Prepare message data
                message_data = {
                    "request_id": message_request.id,
                    "request_type": payload.request_type,
                    "content": payload.content,
                    "meta_data": payload.metadata,
                    "timestamp": datetime.utcnow().isoformat()
                }
                logger.info(json.dumps(message_data, indent=2))
                
                # Create exchange with matching settings
                channel.exchange_declare(
                    exchange=queue_name,
                    exchange_type='direct',
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
                
                task_message = {
                    "task": f"process_{channel_name}_message",
                    "id": str(uuid.uuid4()),
                    "args": [message_data],
                    "kwargs": {}
                }
                
                properties = pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json',
                    content_encoding='utf-8',
                    timestamp=int(time.time())
                )
                
                # Publish to exchange
                channel.basic_publish(
                    exchange=queue_name,
                    routing_key=queue_name,
                    body=json.dumps(task_message),
                    properties=properties
                )
                
                results.append({
                    "channel": channel_name,
                    "status": "published",
                    "task_id": task_message['id']
                })
                
        finally:
            if channel:
                channel.close()
            if connection:
                connection.close()
        
        return {
            "status": "success",
            "request_id": message_request.id,
            "channels": results
        }
        
    except Exception as e:
        logger.error(f"❌ Error in publish_message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to publish message: {str(e)}"
        )

# Pika connection setup
def get_rabbitmq_connection():
    try:
        logger.info(f"Connecting to RabbitMQ at {rabbitmq_host}")
        credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
        parameters = pika.ConnectionParameters(
            host=rabbitmq_host,
            credentials=credentials,
            connection_attempts=5,
            retry_delay=5,
            heartbeat=600
        )
        connection = pika.BlockingConnection(parameters)
        return connection
    except Exception as e:
        logger.error(f"RabbitMQ connection error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"RabbitMQ connection error: {str(e)}")

@app.get("/test-llama")
async def test_llama():
    try:
        # Test Llama connection
        output = replicate.run(
            "meta/llama-2-70b-chat:02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3",
            input={
                "prompt": "Say 'LLM is working' if you can read this.",
                "temperature": 0.1,
                "max_tokens": 10,
            }
        )
        return {
            "status": "success",
            "llm_response": output,
            "api_token_configured": bool(REPLICATE_API_TOKEN)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "api_token_configured": bool(REPLICATE_API_TOKEN)
        }

@app.get("/messages")
async def get_messages(db: Session = Depends(get_db), limit: int = 10):
    messages = db.query(CustomerMessage).order_by(CustomerMessage.created_at.desc()).limit(limit).all()
    return messages

@app.get("/messages/{message_id}")
async def get_message(message_id: int, db: Session = Depends(get_db)):
    message = db.query(CustomerMessage).filter(CustomerMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message

@app.get("/messages/stats")
async def get_message_stats(db: Session = Depends(get_db)):
    stats = {
        "total": db.query(CustomerMessage).count(),
        "by_channel": {}
    }
    
    # Count by channel
    channel_counts = db.query(
        MessageTemplate.channel, 
        func.count(CustomerMessage.id)
    ).join(MessageTemplate).group_by(MessageTemplate.channel).all()
    
    stats["by_channel"] = {c: count for c, count in channel_counts}
    
    return stats

@app.get("/check/{order_id}")
async def check_order_messages(order_id: str, db: Session = Depends(get_db)):
    # Fix the query to properly filter JSON field
    messages = db.query(CustomerMessage).filter(
        CustomerMessage.meta_data.contains({"order_id": order_id})
    ).all()
    
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for this order")
    
    results = []
    for msg in messages:
        templates = db.query(MessageTemplate).filter_by(id=msg.template_id).all()
        results.append({
            "message_id": msg.id,
            "original_content": msg.content,
            "responses": [{
                "channel": t.channel,
                "template": t.template.format(
                    order_id=order_id,
                    tracking_number="TN123456",
                    tracking_url="https://track.com/TN123456"
                )
            } for t in templates]
        })
    
    return results

@app.get("/templates")
async def get_templates(db: Session = Depends(get_db)):
    """Get all available message templates"""
    templates = db.query(MasterTemplate).all()
    return templates

@app.get("/templates/{request_type}")
async def get_templates_by_type(request_type: str, db: Session = Depends(get_db)):
    """Get templates for a specific request type"""
    templates = db.query(MasterTemplate).filter_by(request_type=request_type).all()
    if not templates:
        raise HTTPException(status_code=404, detail=f"No templates found for {request_type}")
    return templates

@app.get("/requests")
async def get_message_requests(
    db: Session = Depends(get_db), 
    limit: int = 10, 
    status: str = None
):
    """Get recent message requests"""
    query = db.query(MessageRequest).order_by(MessageRequest.created_at.desc())
    if status:
        query = query.filter_by(status=status)
    return query.limit(limit).all()

@app.get("/requests/{request_id}")
async def get_message_request(request_id: int, db: Session = Depends(get_db)):
    """Get specific message request"""
    request = db.query(MessageRequest).filter_by(id=request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Message request not found")
    return request

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "publisher",
        "version": "1.0"
    }

if __name__ == "__main__":
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
