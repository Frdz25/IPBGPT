#!/bin/bash

# --- KONFIGURASI ---
REPO_DIR="/path/to/IPBGPT" # GANTI dengan lokasi aktual folder Anda

echo "[$(date)] Starting daily local vector store update pipeline."

# 0. Muat environment variables (termasuk DB credentials)
source "${REPO_DIR}/.env"

# 1. EKSTRAKSI DATABASE KE CSV LOKAL
echo "Running database extraction to local CSV..."
cd "${REPO_DIR}"
# Menjalankan skrip Python baru untuk menyimpan data lokal
/usr/bin/python3 export_db.py 

if [ $? -ne 0 ]; then
    echo "ERROR: Database extraction failed. Aborting indexing."
    exit 1
fi

# 2. Jalankan Proses Indexing Python
echo "Running Python indexer..."
cd "${REPO_DIR}/backend"
# indexer.py akan membaca CSV langsung dari data_source/
/usr/bin/python3 indexer.py 

if [ $? -ne 0 ]; then
    echo "ERROR: Python indexing failed. Check indexer.py logs."
    exit 1
fi

# 3. Restart Server FastAPI (WAJIB)
echo "Restarting FastAPI service to load new vector store..."
sudo /bin/systemctl restart ipbgpt.service

echo "[$(date)] Daily update finished successfully."