# PubSubModel - Multi-Channel Message Publishing System

A distributed messaging system built with FastAPI, Celery, RabbitMQ, and PostgreSQL that enables publishing messages across multiple channels (SMS, Email, WhatsApp) using a pub/sub pattern.

## Architecture

The system consists of four main components:

1. **Publisher Service** (FastAPI) - REST API for publishing messages
2. **Subscriber Service** (Celery) - Worker processes that consume and process messages
3. **RabbitMQ** - Message broker for queue management
4. **PostgreSQL** - Database for storing message requests and templates

## Features

- 📨 Multi-channel messaging (SMS, Email, WhatsApp)
- 📝 Template-based message rendering using Jinja2
- 🗄️ Message request tracking and status management
- 🔄 Asynchronous message processing via Celery workers
- 📊 RESTful API endpoints for message publishing and management
- 🐳 Docker Compose orchestration for easy deployment

## Prerequisites

- Docker and Docker Compose
- (Optional) Twilio account credentials for SMS functionality

## Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/shreyasjha03/PubSubModel.git
cd PubSubModel
```

2. **Configure environment variables (optional)**

For SMS functionality, set Twilio credentials in `subscriber-service`:
```bash
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_phone_number
```

3. **Start the services**
```bash
docker-compose up --build
```

This will start:
- PostgreSQL database on port `5433`
- RabbitMQ management UI on port `15672` (username: `user`, password: `password`)
- Publisher service API on port `8000`
- Subscriber service (Celery worker)

## API Endpoints

### Publisher Service (Port 8000)

#### Publish a Message
```http
POST /publish
Content-Type: application/json

{
  "request_type": "REGISTRATION_SUCCESS",
  "content": {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890"
  },
  "channels": ["email", "sms"],
  "metadata": {
    "user_id": "12345"
  }
}
```

#### Get Message Requests
```http
GET /requests?limit=10&status=pending
```

#### Get Specific Request
```http
GET /requests/{request_id}
```

#### Get Templates
```http
GET /templates
GET /templates/{request_type}
```

#### Health Check
```http
GET /
```

## Message Types

Supported request types:
- `REGISTRATION_SUCCESS` - Welcome messages for new users
- `ORDER_UPDATE` - Order status updates
- `PAYMENT_CONFIRMATION` - Payment receipt notifications

## Supported Channels

- **SMS** - Sends via Twilio (requires Twilio credentials)
- **Email** - Renders HTML templates (currently logs only)
- **WhatsApp** - Placeholder for future implementation

## Project Structure

```
PubSubModel/
├── docker-compose.yml          # Main orchestration file
├── publisher-service/
│   ├── publisher.py            # FastAPI application
│   ├── database.py             # Database models and initialization
│   ├── init_db.py              # Database setup script
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Publisher service container
│   └── start.sh                # Startup script
├── subscriber-service/
│   ├── subscriber.py           # Celery worker application
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Subscriber service container
│   ├── start.sh                # Startup script
│   └── templates/              # Message templates
│       ├── email/
│       │   ├── registration_success.html
│       │   └── order_update.html
│       └── sms/
│           ├── registration_success.txt
│           └── order_update.txt
└── rabbitmq-service/
    └── docker-compose.yml      # RabbitMQ configuration
```

## Database Schema

### master_templates
Stores message templates for different request types and channels.

### message_requests
Tracks all message publishing requests with status and metadata.

## Example Usage

### Publish a Registration Success Message

```bash
curl -X POST http://localhost:8000/publish \
  -H "Content-Type: application/json" \
  -d '{
    "request_type": "REGISTRATION_SUCCESS",
    "content": {
      "name": "Jane Doe",
      "email": "jane@example.com",
      "phone": "+1234567890"
    },
    "channels": ["email", "sms"],
    "metadata": {}
  }'
```

Response:
```json
{
  "status": "success",
  "request_id": 1,
  "channels": [
    {
      "channel": "email",
      "status": "published",
      "task_id": "uuid-here"
    },
    {
      "channel": "sms",
      "status": "published",
      "task_id": "uuid-here"
    }
  ]
}
```

## Configuration

### Environment Variables

**Publisher Service:**
- `DATABASE_URL` - PostgreSQL connection string
- `RABBITMQ_HOST` - RabbitMQ host (default: `rabbitmq`)
- `RABBITMQ_USER` - RabbitMQ username (default: `user`)
- `RABBITMQ_PASS` - RabbitMQ password (default: `password`)

**Subscriber Service:**
- `RABBITMQ_HOST` - RabbitMQ host (default: `rabbitmq`)
- `RABBITMQ_USER` - RabbitMQ username (default: `user`)
- `RABBITMQ_PASS` - RabbitMQ password (default: `password`)
- `TWILIO_ACCOUNT_SID` - Twilio account SID (optional)
- `TWILIO_AUTH_TOKEN` - Twilio auth token (optional)
- `TWILIO_PHONE_NUMBER` - Twilio phone number (optional)

### Database Credentials (default)
- User: `user`
- Password: `password`
- Database: `messagedb`
- Port: `5433`

### RabbitMQ Management UI
- URL: http://localhost:15672
- Username: `user`
- Password: `password`

## Development

### Running Services Individually

**Publisher Service:**
```bash
cd publisher-service
pip install -r requirements.txt
python publisher.py
```

**Subscriber Service:**
```bash
cd subscriber-service
pip install -r requirements.txt
celery -A subscriber worker --loglevel=info -Q sms_queue,email_queue,whatsapp_queue
```

### Database Initialization

The database is automatically initialized on startup. To manually initialize:

```bash
cd publisher-service
python init_db.py
```

## Monitoring

- **Publisher Service Logs**: Check Docker logs for publisher-service
- **Subscriber Service Logs**: Check Docker logs for subscriber-service
- **RabbitMQ Management**: http://localhost:15672
- **Database**: Connect using psql or any PostgreSQL client

## Troubleshooting

1. **Services not starting**: Ensure ports 5433, 5672, 15672, and 8000 are available
2. **RabbitMQ connection errors**: Wait for RabbitMQ to be healthy before starting other services
3. **Database connection errors**: Check PostgreSQL health check status
4. **SMS not sending**: Verify Twilio credentials are set correctly

## License

This project is open source and available for use.

