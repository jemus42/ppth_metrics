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

# Create non-root user but don't switch to it
# Docker metrics require access to Docker socket which needs root or docker group
RUN useradd -m -u 1000 exporter && chown -R exporter:exporter /app
# Running as root for Docker socket access
# USER exporter

# Expose metrics port
EXPOSE 8000

# Run the exporter
CMD ["python", "-u", "metrics.py"]