# etl_loader/Dockerfile
FROM python:3.10-slim

# Set a working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the ETL scripts and entrypoint
COPY transform.py migrate.py test_quality.py entrypoint.sh ./

# Fix line endings and make executable
RUN dos2unix entrypoint.sh && chmod +x entrypoint.sh

# When this container starts, run the full pipeline
ENTRYPOINT ["./entrypoint.sh"]