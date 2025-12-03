#!/bin/bash

# --- KONFIGURASI ---
REPO_DIR="/path/to/ipbgptserver-main" # GANTI dengan path asli Anda!
BACKEND_DIR="${REPO_DIR}/backend"
LIVE_STORE_DIR="${REPO_DIR}/vector_store"
TEMP_STORE_DIR="${REPO_DIR}/vector_store_temp"
BACKUP_STORE_DIR="${REPO_DIR}/vector_store_backup"

echo "[$(date)] --- STARTING ZERO-DOWNTIME UPDATE ---"

# 0. Muat Environment
source "${REPO_DIR}/.env"

# 1. EKSTRAKSI DATABASE
echo "-> 1. Extracting Database..."
cd "${REPO_DIR}"
/usr/bin/python3 export_db.py 
if [ $? -ne 0 ]; then
    echo "❌ Database extraction failed. Aborting."
    exit 1
fi

# 2. PERSIAPAN STAGING (FOLDER SEMENTARA)
echo "-> 2. Preparing Staging Environment..."

# [CRITICAL CLEANUP] Hapus folder temp sisa run kemarin (jika ada)
if [ -d "$TEMP_STORE_DIR" ]; then
    echo "   Cleaning up old temp directory..."
    rm -rf "$TEMP_STORE_DIR"
fi
mkdir -p "$TEMP_STORE_DIR"

# [CRITICAL CLEANUP] Hapus checkpoint agar indexing mulai dari 0 (Fresh Full Re-index)
# Ini penting agar data hari ini benar-benar mencerminkan kondisi terbaru
if [ -f "${BACKEND_DIR}/indexing_checkpoint.txt" ]; then
    rm "${BACKEND_DIR}/indexing_checkpoint.txt"
fi

# 3. JALANKAN INDEXER KE FOLDER TEMP
echo "-> 3. Running Indexer (Target: $TEMP_STORE_DIR)..."
cd "${BACKEND_DIR}"

# Set Environment Variable agar indexer menulis ke folder temp
export VECTOR_STORE_TARGET="$TEMP_STORE_DIR"

# Jalankan Indexer
/usr/bin/python3 indexer.py 

# Cek Status Indexing
if [ $? -ne 0 ]; then
    echo "Indexing failed. Live data is UNTOUCHED. Aborting."
    exit 1
fi

echo "Indexing finished successfully to temp folder."

# 4. FOLDER SWAP (ATOMIC SWITCH)
echo "-> 4. Swapping Live Vector Store..."

cd "${REPO_DIR}"

# A. Hapus folder backup lama (dari 2 hari lalu) agar nama folder tersedia
if [ -d "$BACKUP_STORE_DIR" ]; then
    echo "   Removing old backup..."
    rm -rf "$BACKUP_STORE_DIR"
fi

# B. Pindahkan Live saat ini ke Backup
if [ -d "$LIVE_STORE_DIR" ]; then
    echo "   Moving Live to Backup..."
    mv "$LIVE_STORE_DIR" "$BACKUP_STORE_DIR"
fi

# C. Pindahkan Temp ke Live
echo "   Promoting Temp to Live..."
mv "$TEMP_STORE_DIR" "$LIVE_STORE_DIR"

echo "Folders swapped. New data is now in Live directory."

# 5. HOT RELOAD FASTAPI
echo "-> 5. Triggering Hot Reload..."
# Panggil endpoint reload yang ada di main.py
HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8000/admin/reload-index)

if [ "$HTTP_RESPONSE" -eq 200 ]; then
    echo "SUCCESS: Hot Reload triggered. Server is up-to-date."
else
    echo "Warning: Hot Reload failed (Code: $HTTP_RESPONSE). Restarting service..."
    sudo /bin/systemctl restart ipbgpt.service
fi

echo "[$(date)] --- UPDATE COMPLETE ---"