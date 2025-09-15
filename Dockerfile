FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for psutil
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY metrics.py .

# Create non-root user and switch to it
RUN useradd -m -u 1000 exporter && chown -R exporter:exporter /app
USER exporter

# Expose metrics port
EXPOSE 8000

# Run the exporter
CMD ["python", "-u", "metrics.py"]