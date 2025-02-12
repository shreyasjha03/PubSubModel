from database import SessionLocal, MessageTemplate, MessageConfig

def check_database():
    db = SessionLocal()
    try:
        print("\nFound message configurations:")
        configs = db.query(MessageConfig).all()
        if not configs:
            print("No message configurations found!")
            return
        
        for config in configs:
            print(f"\nID: {config.message_id}")
            print(f"Description: {config.description}")
            print(f"Channels: {config.channels}")
            print(f"Template IDs: {config.template_ids}")

        print("\nFound templates:")
        templates = db.query(MessageTemplate).all()
        if not templates:
            print("No templates found!")
            return
        
        for template in templates:
            print(f"\nID: {template.id}")
            print(f"Channel: {template.channel}")
            print(f"Type: {template.template_type}")
            print(f"Template: {template.template}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_database() 