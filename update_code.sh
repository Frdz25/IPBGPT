#!/bin/bash

# Dapatkan direktori skrip berada (agar aman dijalankan dari mana saja)
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

echo "[$(date)] --- STARTING CODE UPDATE ---"

echo "1. Pulling latest code from GitHub..."
git pull origin main

echo "2. Re-building and restarting Docker containers..."
# Menggunakan --build untuk memastikan perubahan kode python dipanggang ulang
# Menggunakan --remove-orphans untuk membersihkan sampah
sudo docker-compose up -d --build --remove-orphans

echo "3. Cleaning up unused images (save space)..."
sudo docker image prune -f

echo "Docker containers are up-to-date."