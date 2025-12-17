from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq 
from services import chat_with_document, get_related_documents, process_pdf_for_chat, chat_with_pdf_context, chat_general_query, clear_temp_folder
from models import ThesisTitle, ChatQuery
import chromadb
import os
import uuid
from typing import Dict, Any

# Import dotenv untuk memuat variabel lingkungan di backend
from dotenv import load_dotenv
load_dotenv() 

# Inisialisasi FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Authorization", "Content-Type"],
)

# --- GLOBAL VARIABLES ---
# Kita buat variabel global agar bisa di-update
embeddings = None
llm = None
vector_store = None
retriever = None

# Global dictionary untuk menyimpan retriever PDF sementara berdasarkan session_id
if 'PDF_SESSIONS' not in globals():
    PDF_SESSIONS = {}

# --- KONFIGURASI KUNCI DAN MODEL ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- KONFIGURASI KUNCI ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 

# --- KONFIGURASI EMBEDDING (GOOGLE AI STUDIO) ---
# Menggunakan model 'models/text-embedding-004' yang gratis & kuat
try:
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")
        
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=GOOGLE_API_KEY
    )
    # print("Success: Google AI Studio Embeddings initialized.")
except Exception as e:
    print(f"FATAL ERROR: Failed to initialize Google Embeddings: {e}")
    embeddings = None

# --- FUNGSI INISIALISASI (LOADER) ---
def initialize_components():
    """Fungsi untuk memuat/memuat ulang model dan vector store."""
    global embeddings, llm, vector_store, retriever
    
    print("Initializing/Reloading AI Components...")

    # 1. Init Embeddings
    try:
        # (Gunakan logika embeddings Anda yang lama di sini)
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
    except Exception as e:
        print(f"Error init embeddings: {e}")

    # 2. Init LLM
    try:
        # (Gunakan logika LLM Anda yang lama di sini)
        llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=2048 
        )
    except Exception as e:
        print(f"Error init LLM: {e}")

    # 3. Init Vector Store & Retriever (INI YANG PENTING DI-RELOAD)
    try:
        if embeddings:
            db_client = chromadb.PersistentClient(path="../vector_store")
            
            # Paksa client untuk membaca ulang dari disk
            # Kadang perlu reset settings, tapi PersistentClient biasanya cukup
            
            vector_store = Chroma(
                client=db_client,
                collection_name="LMITD",
                embedding_function=embeddings
            )
            
            retriever = vector_store.as_retriever(search_kwargs={"k": 7})
            print("Vector Store & Retriever reloaded successfully.")
        else:
            print("Cannot load vector store: Embeddings not ready.")

    except Exception as e:
        print(f"Error init Vector Store: {e}")
        
# --- ENDPOINTS ---

# --- EVENT STARTUP ---
@app.on_event("startup")
async def startup_event():
    # Jalankan saat server pertama kali nyala
    print("--- Server Starting Up ---")
    initialize_components()
    clear_temp_folder()
    
    # Reset variabel global jika perlu
    global PDF_SESSIONS
    PDF_SESSIONS = {}

# --- EVENT HANDLER: SHUTDOWN (Jalan saat server dimatikan/Ctrl+C) ---
@app.on_event("shutdown")
async def shutdown_event():
    print("--- Server Shutting Down ---")
    clear_temp_folder()
    
    # Bersihkan global dictionary
    if 'PDF_SESSIONS' in globals():
        PDF_SESSIONS.clear()

# --- ENDPOINT BARU: HOT RELOAD ---
@app.post("/admin/reload-index")
async def reload_index_endpoint(request: Request):
    """
    Endpoint rahasia untuk memicu reload vector store tanpa restart server.
    Bisa diamankan dengan mengecek header atau token sederhana.
    """

    try:
        initialize_components()
        return {"status": "success", "message": "Vector store reloaded from disk."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    if llm is None or retriever is None or embeddings is None:
        raise HTTPException(status_code=503, detail="Server components not initialized.")

    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF.")

    temp_dir = "../temp_files"
    os.makedirs(temp_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(temp_dir, file_id + ".pdf")

    try:

        content = await file.read() 
        with open(file_path, "wb") as buffer:
            buffer.write(content)    
            
        await file.seek(0) 
        
        pdf_retriever = await process_pdf_for_chat(file_path, embeddings)
        
        global PDF_SESSIONS
        if 'PDF_SESSIONS' not in globals():
            PDF_SESSIONS = {}
            
        PDF_SESSIONS[file_id] = pdf_retriever

        return {"session_id": file_id, "message": "PDF processed successfully"}
    except Exception as e:
        print(f"Error processing PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@app.post("/chat-with-pdf/")
async def api_chat_with_pdf(chat_query: ChatQuery):
    if llm is None or retriever is None:
        raise HTTPException(status_code=503, detail="Server components not initialized.")

    file_id = chat_query.session_id
    if file_id not in PDF_SESSIONS:
        raise HTTPException(status_code=400, detail="No active PDF session found.")
        
    pdf_retriever = PDF_SESSIONS[file_id]

    try:
        result = await chat_with_pdf_context(chat_query, llm, pdf_retriever)
        return result
    except Exception as e:
        print(f"Error in /chat-with-pdf/: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/combined-query-chat/") 
async def api_general_chat(chat_query: ChatQuery):
    """
    Endpoint untuk mode Chat Umum. Menjalankan RAG penuh menggunakan retriever utama (Database Skripsi IPB).
    """
    if llm is None or retriever is None:
        raise HTTPException(status_code=503, detail="Server components not initialized.")
        
    try:
        result = await chat_general_query(chat_query, llm, retriever) 
        return result
    except Exception as e:
        print(f"Error in /combined-query-chat/: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/")
async def api_chat_with_document(chat_query: ChatQuery):
    """
    Endpoint untuk chat dengan dokumen yang dipilih (Database).
    """
    if llm is None or retriever is None:
        raise HTTPException(status_code=503, detail="Server components not initialized.")
        
    try:
        result = await chat_with_document(chat_query, llm)
        return result
    except Exception as e:
        print(f"Error in /chat/: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/related_documents/")
async def api_get_related_documents(thesis: ThesisTitle):
    """
    Endpoint untuk mencari dokumen terkait berdasarkan judul tesis.
    """
    if vector_store is None: 
        raise HTTPException(status_code=503, detail="Server components not initialized.")
        
    try:
        return await get_related_documents(thesis, vector_store)
    
    except Exception as e:
        print(f"Error in /related_documents/: {e}")
        raise HTTPException(status_code=500, detail=str(e))