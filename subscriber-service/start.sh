#!/bin/bash

# Wait for RabbitMQ
echo "Waiting for RabbitMQ..."
until nc -z rabbitmq 5672; do
    sleep 1
done
echo "RabbitMQ is up"

# Create template directories
mkdir -p /app/templates/{email,sms}

# Create default templates if they don't exist
if [ ! -f /app/templates/sms/registration_success.txt ]; then
    echo "Welcome to our service! Your account is ready." > /app/templates/sms/registration_success.txt
fi

if [ ! -f /app/templates/email/registration_success.html ]; then
    cat > /app/templates/email/registration_success.html << EOL
<!DOCTYPE html>
<html>
<body>
    <h1>Welcome!</h1>
    <p>Your account has been created successfully.</p>
</body>
</html>
EOL
fi

# Start Celery worker with retry
max_retries=5
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    echo "Starting Celery worker (attempt $((retry_count + 1)))"
    python -u subscriber.py
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        break
    fi
    
    echo "Worker exited with code $exit_code. Retrying in 5 seconds..."
    sleep 5
    retry_count=$((retry_count + 1))
done

if [ $retry_count -eq $max_retries ]; then
    echo "Failed to start worker after $max_retries attempts"
    exit 1
fi