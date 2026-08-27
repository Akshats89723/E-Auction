# Use official Python runtime as a parent image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV SECRET_KEY="build-time-secret-key-placeholder"

# Set working directory inside container
WORKDIR /app

# Install system dependencies needed for psycopg2, Pillow, reportlab, cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt-get/lists/*

# Copy requirements file and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt daphne

# Copy the rest of the application code
COPY . /app/

# Expose port 8000
EXPOSE 8000

# Run static collection, database migrations, and Daphne ASGI server
CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate && daphne -b 0.0.0.0 -p 8000 core.asgi:application"]
