<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/62059874-cac7-4e7e-ba8d-85459155ef4f" />


# 🎓 IPB-GPT: Research Assistant Chatbot

**IPB-GPT** adalah asisten riset berbasis AI yang dirancang untuk membantu mahasiswa IPB menemukan referensi skripsi dan jurnal yang relevan. Sistem ini menggunakan teknologi **RAG (Retrieval-Augmented Generation)** untuk menjawab pertanyaan akademis berdasarkan database penelitian internal maupun dokumen PDF yang diunggah pengguna.


## ✨ Fitur Utama

- **🔍 Semantic Search:** Pencarian skripsi berdasarkan makna/konteks (bukan hanya keyword) menggunakan Google Generative AI Embeddings.

- **🤖 Chat with Database:** Tanya jawab interaktif dengan seluruh database skripsi menggunakan LLM (Llama-3 via Groq).

- **📄 Chat with PDF:** Unggah file PDF (jurnal/paper) dan diskusi secara spesifik mengenai konten file tersebut.




## 🛠️ Persiapan Awal (Wajib)

Sebelum menjalankan di laptop maupun server, Anda wajib memiliki file konfigurasi env.

1. Clone repositori ini:
```
git clone https://github.com/Frdz25/IPBGPT.git
cd IPBGPT
```

2. Buat file .env di direktori root (sejajar dengan docker-compose.yml):
```
# --- API KEYS (Wajib) ---
GOOGLE_API_KEY=masukkan_google_api_key_disini
GROQ_API_KEY=masukkan_groq_api_key_disini

# --- DATABASE KAMPUS (Target) ---
DB_HOST=localhost       # Biarkan localhost karena diakses via tunnel
DB_NAME=nama_db_ipb
DB_USER=username_db
DB_PASSWORD=password_db
DB_PORT=5432

# --- SSH TUNNEL (Bastion Host) ---
# Diperlukan untuk mengakses DB Kampus dari luar
SSH_HOST=ip_address_server_ssh
SSH_USER=username_ssh
SSH_PASSWORD=password_ssh
SSH_PORT=22
# SSH_KEY_PATH=/path/to/private/key  # Opsional jika menggunakan key file

# --- KONFIGURASI FRONTEND ---
# Jika lokal/server docker, gunakan nama service backend
URL_BASE=http://backend:8000
```

## 💻 Skenario 1: Menjalankan di Device Sendiri (Localhost)

Gunakan cara ini jika Anda ingin mengedit kode atau menjalankan aplikasi di laptop pribadi (Windows/Mac/Linux).

### Prasyarat

- Docker Desktop sudah terinstall dan berjalan.

### Langkah-langkah

1. **Pastikan Koneksi:** Jika database kampus memerlukan VPN, pastikan VPN Anda sudah terkoneksi.

2. **Export Database:** Lakukan export database dengan menjalankan:
```
python export_db
```

Hasil export dari database akan disimpan dalam bentuk file paper_metadata.csv pada folder data_source di direktori utama. Pastikan file .env sudah terkonfigurasi.

3. **Buat Vector Store:** Dari paper_metadata.csv perlu kita ubah menjadi vector database dengan menjalankan:
```
python indexer.py
```

Proses ini dapat memakan waktu yang cukup lama dan juga menggunakan CPU dan Memory yang besar. Hasilnya adalah sebuah folder vector_store yang berada pada direktori utama. Folder ini data adalah yang akan digunakan untuk embedding search dan juga data yang akan digunakan oleh LLM.

2. **Jalankan Docker Compose:**
Buka terminal di folder project, lalu jalankan:
```
docker-compose up -d --build
```

3. **Akses Aplikasi:**

**Frontend (Chat):** Buka browser ke http://localhost:8501

**Backend (Swagger UI):** Buka browser ke http://localhost:8000/docs

**Portainer (Monitoring):** Buka browser ke http://localhost:9000

4. **Menghentikan Aplikasi:**
Jalankan kode dibawah ini:
```
docker-compose down
```
**Catatan Lokal:** Jika koneksi SSH gagal (misal karena tidak ada VPN) ketika ekstraksi data, aplikasi mungkin error. Anda bisa meletakkan file dummy paper_metadata.csv di folder data_source/ secara manual jika tidak ingin menghubungkan ke DB asli.

## ☁️ Skenario 2: Deployment di Server (VPS/Production)

Gunakan cara ini untuk deployment stabil di server (Ubuntu/Debian) dengan fitur update otomatis.

### Prasyarat

- Server Linux dengan Docker & Docker Compose terinstall.

- Akses Git ke repositori ini.

### Langkah-langkah Deployment

1. **Beri Izin Eksekusi pada Script:**
Agar script maintenance bisa berjalan, ubah permission-nya:
```
chmod +x update_code.sh startup.sh update_cron.sh
```

2. **Jalankan Script Instalasi:**
Gunakan script update_code.sh untuk menarik kode terbaru, membangun image, dan menyalakan container:
```
./update_code.sh
```

3. **Inisialisasi Data Awal:**
Jalankan script startup untuk menarik data dari DB kampus dan melakukan indexing pertama kali:
```
./startup.sh
```

Proses ini mungkin memakan waktu tergantung besarnya data.

4. **Aktifkan Jadwal Otomatis (Cron Job):**
Agar data selalu update setiap malam (pukul 02:00) tanpa mematikan server:
```
./update_cron.sh
```

### Cara Maintenance di Server

- **Update Kode Aplikasi:** Jika Anda melakukan push kode baru ke GitHub, cukup jalankan:
```
./update_code.sh
```

- **Cek Log Update Data:**
```
tail -f update_cron.log
```

## 🤖 Penjelasan Script Otomatisasi

Folder root proyek ini berisi beberapa script BASH untuk mempermudah pengelolaan server:

| Nama Script | Fungsi & Deskripsi |
| - | - |
| `startup.sh` | Zero-Downtime Data Pipeline. Script ini mengekstrak data dari DB, membuat index vektor baru di background, lalu menukar (swap) folder index lama dengan yang baru secara instan. User tidak akan merasakan server down saat update data terjadi. |
| `update_code.sh` | Code Deployment. Melakukan git pull untuk mengambil kode Python terbaru, lalu melakukan docker compose up --build untuk menerapkan perubahan tersebut. |
| `update_cron.sh` | Auto-Scheduler. Mendaftarkan startup.sh ke dalam sistem Cron Linux agar berjalan otomatis setiap hari pukul 02:00 pagi. |

## 📂 Struktur Folder

    IPB-GPT/
    ├── backend/                # Kode Python Backend (FastAPI)
    │   ├── export_db.py        # Script ekstraksi DB via SSH
    │   ├── indexer.py          # Script embedding & ChromaDB
    │   └── ...
    ├── frontend/               # Kode Python Frontend (Streamlit)
    │   ├── ui_components.py    # Komponen Tampilan
    │   └── ...
    ├── data_source/            # Folder mounting untuk CSV mentah
    ├── vector_store/           # Folder mounting untuk Database Vektor (Live)
    ├── docker-compose.yml      # Konfigurasi Container
    └── *.sh                    # Script maintenance

📝 Lisensi

Project ini dikembangkan untuk keperluan riset dan akademik.