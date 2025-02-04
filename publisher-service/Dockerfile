FROM python:3.9-slim

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000

# Add environment variables to prevent Python from buffering logs
ENV PYTHONUNBUFFERED=1

# Change the CMD to use Python directly
CMD ["python", "-u", "publisher.py"]
