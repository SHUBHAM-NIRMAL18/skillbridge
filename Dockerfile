# Use official Python lightweight runtime base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (build tools, PostgreSQL client, WeasyPrint dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files into container
COPY . /app/

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Expose port 8000
EXPOSE 8000

# Set entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command to start Gunicorn server
CMD ["gunicorn", "skillbridge.wsgi:application", "--bind", "0.0.0.0:8000"]
