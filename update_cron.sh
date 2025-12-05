#!/bin/bash

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="${BASE_DIR}/cron_update.log"
TARGET_SCRIPT="${BASE_DIR}/startup.sh"

# Perintah Cron: Jalan jam 02:00 setiap hari
CRON_CMD="0 2 * * * /bin/bash ${TARGET_SCRIPT} >> ${LOG_FILE} 2>&1"

# 1. Berikan izin eksekusi
chmod +x "$TARGET_SCRIPT"
chmod +x "${BASE_DIR}/update_code.sh"

# 2. Update Crontab
# Hapus entry lama jika ada (biar tidak duplikat)
(crontab -l 2>/dev/null | grep -v "${TARGET_SCRIPT}") | crontab -
# Tambahkan entry baru
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "Cron job successfully updated."
echo "   Command: $CRON_CMD"

# 3. Test Run (Opsional - Jalankan startup.sh sekarang untuk tes)
# read -p "Do you want to run the update pipeline NOW for testing? (y/n) " -n 1 -r
# echo
# if [[ $REPLY =~ ^[Yy]$ ]]
# then
#     /bin/bash "$TARGET_SCRIPT"
# fi