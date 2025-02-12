FROM python:3.9-slim

# Install PostgreSQL client
RUN apt-get update && apt-get install -y postgresql-client netcat-openbsd && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Make the startup script executable
RUN chmod +x start.sh

# Environment variables for logging
ENV PYTHONUNBUFFERED=1

# Run the startup script
CMD ["./start.sh"]
