from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Connection string
DATABASE_URL = "postgresql://user:password@localhost:5432/messagedb"

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Get all messages
messages = db.query(MessageLog).all()
for msg in messages:
    print(f"ID: {msg.id}")
    print(f"Type: {msg.message_type}")
    print(f"Priority: {msg.priority}")
    print(f"Content: {msg.content}")
    print(f"Created: {msg.created_at}")
    print(f"Metadata: {msg.metadata}")
    print("-" * 50)

# Close session
db.close() 