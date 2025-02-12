from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from datetime import datetime
from sqlalchemy.orm import Session

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/messagedb")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class MasterTemplate(Base):
    __tablename__ = "master_templates"

    id = Column(Integer, primary_key=True)
    request_type = Column(String)  # e.g., ORDER_UPDATE, REGISTRATION_SUCCESS, PAYMENT_CONFIRMATION
    channel = Column(String)  # sms, email, whatsapp
    template = Column(String)
    meta_data = Column(JSON)  # Additional template metadata

class MessageRequest(Base):
    __tablename__ = "message_requests"

    id = Column(Integer, primary_key=True)
    request_type = Column(String)  # Maps to master_templates.request_type
    content = Column(JSON)  # Dynamic content for template
    status = Column(String, default="PENDING")  # PENDING, PROCESSED, FAILED
    channels = Column(JSON)  # Which channels to use
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    meta_data = Column(JSON)  # Additional request metadata

    @staticmethod
    def get_template(request_type: str, channel: str, db: Session) -> MasterTemplate:
        return db.query(MasterTemplate).filter_by(
            request_type=request_type,
            channel=channel
        ).first()

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # Clear existing data
        db.query(MasterTemplate).delete()
        
        # Add templates for different request types
        templates = [
            # Order Update Templates
            MasterTemplate(
                request_type="ORDER_UPDATE",
                channel="sms",
                template="Your order {order_id} status: {status}. {message}",
                meta_data={"type": "notification"}
            ),
            MasterTemplate(
                request_type="ORDER_UPDATE",
                channel="email",
                template="""
                Dear {customer_name},
                
                Your order {order_id} status has been updated.
                
                Status: {status}
                {message}
                
                Track your order: {tracking_url}
                
                Best regards,
                Your Company
                """,
                meta_data={"type": "notification"}
            ),
            
            # Registration Templates
            MasterTemplate(
                request_type="REGISTRATION_SUCCESS",
                channel="email",
                template="""
                Welcome {customer_name}!
                
                Your account has been successfully created.
                
                Start exploring our services here: {dashboard_url}
                
                Best regards,
                Your Company
                """,
                meta_data={"type": "onboarding"}
            ),
            MasterTemplate(
                request_type="REGISTRATION_SUCCESS",
                channel="sms",
                template="Welcome to Our Service! Your account has been created successfully. Login here: {login_url}",
                meta_data={"type": "onboarding"}
            ),
            
            # Payment Templates
            MasterTemplate(
                request_type="PAYMENT_CONFIRMATION",
                channel="email",
                template="""
                Dear {customer_name},
                
                We've received your payment of {amount} for order {order_id}.
                
                Transaction ID: {transaction_id}
                Date: {payment_date}
                
                View receipt: {receipt_url}
                
                Thank you for your business!
                Your Company
                """,
                meta_data={"type": "transaction"}
            ),
            MasterTemplate(
                request_type="PAYMENT_CONFIRMATION",
                channel="sms",
                template="Payment received: {amount} for order {order_id}. Receipt: {receipt_url}",
                meta_data={"type": "transaction"}
            )
        ]
        
        for template in templates:
            db.add(template)
        
        db.commit()
        print("Database initialized with templates!")
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 