# Gunakan base image Python yang ringan
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependensi sistem
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dan install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode backend
COPY . .

# Expose port
EXPOSE 8000

# Perintah menjalankan aplikasi
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]