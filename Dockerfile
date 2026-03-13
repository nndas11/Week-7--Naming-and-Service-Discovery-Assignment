FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY service_registry_improved.py .
COPY example_service.py .
COPY registry_client.py .
COPY service_common.py .
COPY cart_service.py .
COPY payment_service.py .
COPY client.py .

# Expose port
EXPOSE 5001

# Run the registry by default
CMD ["python", "service_registry_improved.py"]
