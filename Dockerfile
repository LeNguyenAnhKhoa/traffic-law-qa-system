# Sử dụng Python 3.11 slim
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements từ backend
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ backend code
COPY backend/ .

# Expose port
EXPOSE 5000

# Command để chạy
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-5000}