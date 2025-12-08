<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/62059874-cac7-4e7e-ba8d-85459155ef4f" />


# 🎓 IPB-GPT: Research Assistant

IPB-GPT adalah asisten riset cerdas berbasis Retrieval-Augmented Generation (RAG) yang dirancang untuk membantu mahasiswa dan peneliti IPB dalam mencari, menelaah, dan berinteraksi dengan literatur akademik (Skripsi/Tesis).

Sistem ini menggabungkan kekuatan Llama 3 (via Groq) untuk kecepatan inferensi tinggi dan Google Generative AI Embeddings untuk pencarian semantik yang akurat.


# ✨ Fitur Utama

## 1. 🔍 Search & Chat (RAG Skripsi IPB)

Pencarian Semantik: Mencari dokumen yang relevan bukan hanya berdasarkan kata kunci, tapi berdasarkan makna/konteks dari judul dan abstrak.

Database Besar: Terhubung dengan database metadata skripsi IPB yang di-indeks menggunakan ChromaDB.

Kutipan Akurat: Jawaban AI dilengkapi dengan judul dan link URL ke repositori asli untuk validasi sumber.

## 2. 📄 Chat with PDF (Analisis Dokumen Pribadi)

Upload & Tanya: Pengguna dapat mengunggah file PDF jurnal/skripsi sendiri secara ad-hoc.

Sesi Terisolasi: File PDF diproses secara in-memory dan terisolasi per sesi pengguna.

Ringkasan Cepat: Minta AI merangkum, mencari metode, atau menjelaskan kesimpulan dari PDF tersebut.



# 🚀 Cara Menjalankan (Installation)

Prasyarat

Docker & Docker Compose (Sangat Disarankan)

Git

API Key dari Groq dan Google AI Studio.

### Metode 1: Menggunakan Docker

Ini adalah cara termudah karena tidak perlu setup environment Python manual.

Clone Repository:

git clone https://github.com/Frdz25/IPBGPT.git

cd IPBGPT


Setup Environment Variables:
Buat file .env di root folder dan isi konfigurasi (lihat contoh di bawah).

Jalankan Aplikasi:

docker-compose up -d --build


Akses Aplikasi:

Frontend (Chat): Buka http://localhost:8501

Backend (API Docs): Buka http://localhost:8000/docs



### Metode 2: Menjalankan Manual (Development)

Jika ingin menjalankan tanpa Docker untuk keperluan coding/debugging.

Terminal 1 (Backend):

cd backend

python -m venv venv

source venv/bin/activate  # atau .\venv\Scripts\activate di Windows

pip install -r requirements.txt

uvicorn main:app --reload --port 8000


Terminal 2 (Frontend):

cd frontend

python -m venv venv

source venv/bin/activate  # atau .\venv\Scripts\activate di Windows

pip install -r requirements.txt

streamlit run main.py


# 🔑 Konfigurasi (.env)

Buat file bernama .env di root folder project. Jangan lupa isi kredensial berikut:

--- AI Provider Keys ---

GROQ_API_KEY=...

GOOGLE_API_KEY=...


# 📂 Struktur Project

    ipb-gpt/
    ├── docker-compose.yml       # Konfigurasi Orchestration
    ├── .env                     # File Konfigurasi (JANGAN DI-PUSH)
    ├── vector_store/            # Folder Database Vektor (Chroma)
    ├── backend/                 # API Server
    │   ├── main.py              # Entry point FastAPI
    │   ├── services.py          # Logika RAG & LLM
    │   ├── indexer.py           # Skrip embedding data skripsi
    │   ├── models.py            # Logika model
    │   ├── export_db.py         # Export data dari database
    │   └── requirements.txt
    └── frontend/                # User Interface
        ├── main.py              # Entry point Streamlit
        ├── ui_components.py     # Komponen UI
        ├── app_modes.py         # Mode aplikasi
        ├── chat_logic.py        # Logika chat
        ├── document_processing.py
        └── requirements.txt



📝 License

Project ini dikembangkan untuk keperluan riset dan akademik.