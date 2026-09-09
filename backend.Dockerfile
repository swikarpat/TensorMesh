# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
# Increase timeout to 1000 seconds to prevent network drops on large ML libraries
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copy the Python package
COPY tensormesh/ ./tensormesh/

# Expose the FastAPI port
EXPOSE 8000

# Command to run the backend
CMD ["uvicorn", "tensormesh.api.main:app", "--host", "0.0.0.0", "--port", "8000"]