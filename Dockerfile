# Python base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and CRM database
COPY . .

# Expose port (Render automatically provides $PORT)
EXPOSE 8090

# Run the CRM FastAPI application
CMD ["python", "main.py"]
