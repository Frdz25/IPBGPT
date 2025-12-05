#!/bin/bash

# --- KONFIGURASI ---
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_CONTAINER="ipb_backend" # Nama container sesuai docker-compose
LIVE_STORE_DIR="${BASE_DIR}/vector_store"
TEMP_STORE_DIR="${BASE_DIR}/vector_store_temp"
BACKUP_STORE_DIR="${BASE_DIR}/vector_store_backup"

echo "[$(date)] --- STARTING ZERO-DOWNTIME UPDATE (DOCKER MODE) ---"

# 1. PERSIAPAN FOLDER STAGING (Di Host)
echo "-> 1. Preparing Staging Environment..."
if [ -d "$TEMP_STORE_DIR" ]; then
    rm -rf "$TEMP_STORE_DIR"
fi
# Kita buat folder temp di host, yang nanti akan 'terlihat' oleh docker 
# karena kita akan mapping volume sementara atau copy hasil akhirnya.
mkdir -p "$TEMP_STORE_DIR"

# 2. EKSTRAKSI DATABASE (Jalankan DI DALAM Docker)
echo "-> 2. Extracting Database (inside container)..."
# Menjalankan export_db.py menggunakan environment python di dalam container
docker exec "$BACKEND_CONTAINER" python export_db.py

if [ $? -ne 0 ]; then
    echo "Database extraction failed inside container. Aborting."
    exit 1
fi

# 3. INDEXING KE FOLDER TEMP
echo "-> 3. Running Indexer..."

# Trik: Kita set env var KHUSUS untuk perintah ini saja
# Kita asumsikan indexer.py akan menulis ke folder /app/vector_store_temp di dalam container
# Nanti kita copy keluar.
docker exec -e VECTOR_STORE_TARGET="vector_store_temp" "$BACKEND_CONTAINER" python indexer.py

if [ $? -ne 0 ]; then
    echo "Indexing failed. Live data is UNTOUCHED. Aborting."
    exit 1
fi

echo "Indexing finished inside container."

# 4. AMBIL DATA DARI CONTAINER KE HOST (Copy Out)
echo "-> 4. Syncing new index to Host..."
# Menyalin folder temp dari dalam container ke folder temp Host
docker cp "${BACKEND_CONTAINER}:/app/vector_store_temp/." "$TEMP_STORE_DIR"

# 5. FOLDER SWAP (Di Host)
echo "-> 5. Swapping Live Vector Store..."

# A. Backup Live
if [ -d "$LIVE_STORE_DIR" ]; then
    if [ -d "$BACKUP_STORE_DIR" ]; then
        rm -rf "$BACKUP_STORE_DIR"
    fi
    mv "$LIVE_STORE_DIR" "$BACKUP_STORE_DIR"
fi

# B. Promosi Temp jadi Live
mv "$TEMP_STORE_DIR" "$LIVE_STORE_DIR"

echo "Folders swapped. New data is active on Host Volume."

# 6. HOT RELOAD / RESTART
echo "-> 6. Triggering Reload..."

# Coba Hot Reload via API (Pastikan IP/Port benar)
# Kita tembak ke localhost:8000 karena di server port 8000 terbuka
HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/admin/reload-index)

if [ "$HTTP_RESPONSE" -eq 200 ]; then
    echo "SUCCESS: Hot Reload triggered via API."
else
    echo "Hot Reload API failed (Code: $HTTP_RESPONSE). Restarting Backend Container..."
    # Restart container Docker (bukan systemctl)
    docker restart "$BACKEND_CONTAINER"
fi

echo "[$(date)] --- UPDATE COMPLETE ---"