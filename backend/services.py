from fastapi import HTTPException
from fastapi.responses import JSONResponse
from models import ChatQuery, ThesisTitle, ChatMessage
from typing import List
import shutil
import time
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

# --- FUNGSI PROMPT ---

def generate_academic_answer_prompt(chat_history: str, context: str, query: str, is_follow_up: bool = False) -> str:
    """
    Menghasilkan prompt yang ketat untuk mode RAG (dengan konteks dokumen).
    """
    system_instruction = f"""
Anda adalah asisten yang berpengetahuan luas dan ramah yang menjawab pertanyaan berdasarkan **KONTEKS** yang disediakan. Anda HARUS BERTINDAK SEBAGAI ASISTEN PENELITI.

## ATURAN KONTEN
1. **Dasar Jawaban:** Jawaban Anda HANYA BOLEH didasarkan pada informasi yang ada di bagian `CONTEXT`. JANGAN menggunakan pengetahuan umum atau informasi eksternal.
2. **Kualitas Jawaban:** Berikan jawaban yang bijaksana, rinci, dan jelas.
3. **KUTIPAN DAN SUMBER (PENTING):** - Setiap kali Anda memberikan informasi spesifik dari dokumen, Anda WAJIB menyertakan judul dan URL sumbernya.
    - Format kutipan: "[Judul Dokumen](URL)".
    - Jika URL bernilai "No URL" atau kosong, tuliskan judulnya saja.
4. **Token Selesai:** Jika jawaban yang diberikan sepenuhnya dan memuaskan menjawab pertanyaan berdasarkan konteks, akhiri respons Anda dengan token ini: '<|reserved_special_token_0|>'

## ATURAN FORMATTING
Format SEMUA respons secara konsisten menggunakan panduan Markdown ini:
1. Gunakan HANYA sintaks Markdown untuk SEMUA format.
2. JANGAN PERNAH menggunakan ``` untuk teks biasa, hanya gunakan untuk KODE.
3. JANGAN PERNAH menggunakan HTML atau CSS.
4. Struktur: Mulai dengan ringkasan/pendahuluan singkat (1-4 kalimat).
5. Untuk daftar:
    - Gunakan 1., 2., 3. untuk item berurutan atau prioritas.
    - Gunakan - untuk daftar tidak berurutan.
    - Gunakan indentasi yang konsisten untuk daftar bersarang.
"""

    prompt = f"""
{system_instruction}

Chat history:
{chat_history}

Context:
{context}

Question: {query}

[JAWABAN]
"""
    return prompt

# --- FUNGSI PEMBERSIH RESPONS ---

def clean_response(raw_response: str) -> str:
    """
    Membersihkan respons mentah dari LLM dengan mencari tag jawaban yang sangat eksplisit 
    dan menghapus semua teks prompt, konteks, dan karakter yang tidak diinginkan.
    """
    answer_tag = "[JAWABAN]" 
    raw_text_lower = raw_response.lower()
    clean_text = raw_response
    
    # 1. Cari posisi tag jawaban yang sangat eksplisit
    if answer_tag.lower() in raw_text_lower:
        # Temukan indeks mulai dari tag '[JAWABAN]'
        start_index = raw_text_lower.rfind(answer_tag.lower())
        
        # Ambil teks setelah tag (panjang '[JAWABAN]' adalah 9)
        clean_text = raw_response[start_index + len(answer_tag):]
    
    # 2. Hapus token selesai (jika ada)
    clean_text = clean_text.replace('<|reserved_special_token_0|>', '')

    # 3. Pembersihan Karakter Aneh (Unicode/Kontrol)
    clean_text = clean_text.encode('ascii', 'ignore').decode('ascii')

    # 4. Pembersihan Akhir: Hapus spasi dan quote yang tersisa di awal/akhir
    return clean_text.strip().strip("'").strip('"').strip()

# --- DEFINISI FUNGSI PEMBERSIH TEMP FOLDER ---

def clear_temp_folder():
    """Fungsi sinkronus untuk menghapus folder."""
    temp_dir = "../temp_files"
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            # print(f"Cleaned up: {temp_dir}")
        except Exception as e:
            print(f"Error deleting temp folder: {e}")
    
    # Buat ulang folder kosong agar siap dipakai
    os.makedirs(temp_dir, exist_ok=True)

# --- FUNGSI PDF UPLOAD ---

async def process_pdf_for_chat(file_path: str, embeddings):
    """Memproses PDF, membagi teks, dan membuat Chroma vector store sementara."""
    try:
        # 1. Muat Dokumen
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        if not documents:
            raise ValueError("No text extracted from PDF.")

        # 2. Split Dokumen
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200, 
            length_function=len,
            is_separator_regex=False
        )
        texts = text_splitter.split_documents(documents)

        # 3. Buat Chroma Vector Store Sementara (in-memory, tanpa client persistent)
        vectorstore = Chroma.from_documents(
            documents=texts,
            embedding=embeddings
        )

        # 4. Kembalikan Retriever LangChain
        return vectorstore.as_retriever(search_kwargs={"k": 10}) 

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Processing Error: {str(e)}")


# --- FUNGSI CHAT UMUM ---
async def chat_general_query(chat_query: ChatQuery, llm, general_retriever):
    """
    Menangani permintaan chat umum (Chat Mode) dengan mengintegrasikan RAG
    menggunakan retriever utama (database skripsi).
    """
    start_time = time.time()
    try:
        # 1. Retrieval (Ambil konteks dari database utama)
        relevant_docs = general_retriever.invoke(chat_query.query) 
        context_list = []
        for doc in relevant_docs:
            # Ambil metadata yang sudah di-index di indexer.py
            judul = doc.metadata.get("title", "Tanpa Judul")
            url = doc.metadata.get("uri", "URL Tidak Tersedia")
            isi = doc.page_content
            
            # Format ulang agar LLM tahu mana URL-nya
            formatted_doc = f"JUDUL: {judul}\nURL: {url}\nISI: {isi}"
            context_list.append(formatted_doc)

        context = "\n\n---\n\n".join(context_list)
        
        # --- PERBAIKAN: HANYA CEK KONTEKS ---
        if not context:
             # Jawaban fallback yang formal, dipicu jika retrieval gagal
             response_text = "Saya adalah asisten riset IPB. Saat ini saya belum menemukan dokumen yang relevan di database penelitian kami untuk menjawab pertanyaan Anda."
             return JSONResponse(content={"response": response_text})

        # 3. Formatting Chat History
        limited_chat_history = chat_query.chat_history[-3:]
        chat_history = "\n".join(f"{msg.role}: {msg.content}" for msg in limited_chat_history)
        
        # 4. Generation (Buat prompt RAG dan panggil LLM)
        prompt = generate_academic_answer_prompt(chat_history, context, chat_query.query)
        response = llm.invoke(prompt)
        
        # --- PEMBERSIHAN RESPONS ---
        final_response = clean_response(str(response.content))

        process_time = time.time() - start_time
        print(f"General chat (RAG) request took {process_time:.4f} seconds")
        
        return JSONResponse(content={"response": final_response})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- FUNGSI CHAT PDF ---

async def chat_with_pdf_context(chat_query, llm, pdf_retriever):
    """Menangani chat dengan dokumen PDF yang diunggah menggunakan retriever LangChain."""
    start_time = time.time()
    
    try:
        # 1. Retrieval (Ambil konteks dari PDF)
        relevant_docs = pdf_retriever.invoke(chat_query.query) 
        context = "\n\n".join([doc.page_content for doc in relevant_docs])

        if not context:
            response_text = "Saya telah memproses PDF Anda, tetapi tidak menemukan informasi yang relevan untuk pertanyaan ini dalam dokumen tersebut."
            return JSONResponse(content={"response": response_text})
        
        # 2. Formatting Chat History
        limited_chat_history = chat_query.chat_history[-3:]
        chat_history = "\n".join(f"{msg.role}: {msg.content}" for msg in limited_chat_history)
        
        # 3. Generation (Buat prompt dan panggil LLM)
        prompt = generate_academic_answer_prompt(chat_history, context, chat_query.query)
        response = llm.invoke(prompt)
        
        # --- PEMBERSIHAN RESPONS ---
        final_response = clean_response(str(response.content))


        process_time = time.time() - start_time
        print(f"Chat with PDF request took {process_time:.4f} seconds")
        
        return JSONResponse(content={"response": final_response})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- FUNGSI get_related_documents ---

async def get_related_documents(thesis: ThesisTitle, retriever):
    """Mengambil dokumen terkait dari Chroma DB menggunakan LangChain Retriever."""
    try:
        # Gunakan LangChain retriever
        related_documents = retriever.invoke(thesis.title)
        
        results = []
        for doc in related_documents:
            # Mengambil data langsung dari .metadata karena sudah disimpan di indexer.py
            # dengan nama kolom asli: 'title', 'abstract', 'uri'
            
            judul = doc.metadata.get("title", "Judul Tidak Ditemukan")
            url = doc.metadata.get("uri", "No URL")
            
            # Abstrak diambil dari metadata atau page_content (jika page_content berisi abstrak)
            # Karena page_content di indexer.py adalah Judul + Abstrak, lebih baik ambil dari metadata.
            abstrak = doc.metadata.get("abstract", doc.page_content) 

            results.append({
                # Pastikan key (judul, abstrak, url) sesuai dengan yang diharapkan frontend
                "judul": judul.strip(), 
                "abstrak": abstrak.strip(),
                "url": url.strip()
            })

        return {"related_documents": results}
    except Exception as e:
        # Log error untuk debugging
        print(f"Error in get_related_documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- FUNGSI chat_with_document ---

async def chat_with_document(chat_query: ChatQuery, llm):
    """Menangani chat dengan dokumen yang dipilih (Database) menggunakan LLM LangChain."""
    start_time = time.time()
    try:
        limited_chat_history = chat_query.chat_history[-3:]
        chat_history = "\n".join(f"{msg.role}: {msg.content}" for msg in limited_chat_history)
        prompt = generate_academic_answer_prompt(chat_history, chat_query.context, chat_query.query)
        
        # Menggunakan llm.invoke() LangChain
        response = llm.invoke(prompt)

        # --- PEMBERSIHAN RESPONS ---
        final_response = clean_response(str(response.content))

        process_time = time.time() - start_time
        print(f"Chat with document request took {process_time:.4f} seconds")
        
        return JSONResponse(content={"response": final_response})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))