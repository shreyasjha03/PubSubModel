# Dockerfile for Subscriber (Celery Worker)
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the subscriber code
COPY . .

# Environment variables for logging
ENV PYTHONUNBUFFERED=1

# Run the Celery worker
CMD ["celery", "-A", "subscriber", "worker", "--loglevel=info", "--concurrency=1"]
