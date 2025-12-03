# Gunakan Python yang ringan
FROM python:3.10-slim

WORKDIR /app

# Copy requirements frontend dan install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode frontend
COPY . .

# Expose port default Streamlit
EXPOSE 8501

# Perintah menjalankan Streamlit
# address 0.0.0.0 penting agar bisa diakses dari luar container
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]