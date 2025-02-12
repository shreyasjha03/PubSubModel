from database import init_db, engine, Base, SessionLocal, MasterTemplate, MessageRequest

def main():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
    
    print("\nInitializing database...")
    init_db()
    
    # Verify the setup
    db = SessionLocal()
    try:
        print("\nVerifying database setup...")
        
        # Check master templates
        templates = db.query(MasterTemplate).all()
        print(f"\nFound {len(templates)} master templates:")
        for template in templates:
            print(f"\nRequest Type: {template.request_type}")
            print(f"Channel: {template.channel}")
            print(f"Template: {template.template[:50]}...")
            print("-" * 50)
        
        # Check message requests
        requests = db.query(MessageRequest).all()
        print(f"\nFound {len(requests)} message requests:")
        for req in requests:
            print(f"\nID: {req.id}")
            print(f"Request Type: {req.request_type}")
            print(f"Status: {req.status}")
            print(f"Channels: {req.channels}")
            print("-" * 50)
            
    finally:
        db.close()

if __name__ == "__main__":
    main() 