# Sử dụng Python 3.11 slim để giảm kích thước image
FROM python:3.11-slim

# Set working directory trong container
WORKDIR /app

# Copy file requirements trước để tận dụng Docker layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ source code
COPY . .

# Expose port 5000 (port mà FastAPI chạy)
EXPOSE 5000

# Command để chạy ứng dụng
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]