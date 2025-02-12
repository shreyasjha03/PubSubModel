# Dockerfile for Subscriber (Celery Worker)
FROM python:3.9-slim

# Install netcat for health check
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create a non-root user
RUN groupadd -r celery && useradd -r -g celery celery

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and templates
COPY . .
COPY templates /app/templates

# Set proper permissions
RUN chown -R celery:celery /app

# Make the start script executable
RUN chmod +x start.sh

# Switch to non-root user
USER celery

CMD ["./start.sh"]
