import pandas as pd
import chromadb
import time
import os
import sys
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DataFrameLoader
from dotenv import load_dotenv

load_dotenv()

# --- KONFIGURASI DINAMIS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path Vector Store
DEFAULT_STORE_PATH = os.path.join(BASE_DIR, "..", "vector_store")
VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_TARGET", DEFAULT_STORE_PATH)

# --- PATH DATA SOURCE ---
# Mengarah ke folder sejajar backend: ../data_source
SOURCE_DATA_PATH = os.path.join(BASE_DIR, "..", "data_source", "paper_metadata.csv")
SOURCE_DATA_PATH = os.path.normpath(SOURCE_DATA_PATH)

COLLECTION_NAME = "LMITD"
CHECKPOINT_FILE = os.path.join(BASE_DIR, "logs", "indexer_checkpoint.txt")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY tidak ditemukan!")

def run_indexing():
    print("--- Starting Indexer ---")
    print(f"Reading from: {SOURCE_DATA_PATH}")
    
    if not os.path.exists(SOURCE_DATA_PATH):
        print(f"FATAL: Data source not found at {SOURCE_DATA_PATH}.")
        return False
        
    try:
        # 1. Initialize Embeddings
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=GOOGLE_API_KEY,
            task_type="retrieval_document"
        )
        print("Embeddings initialized.")
        
        # 2. Muat Data
        df = pd.read_csv(SOURCE_DATA_PATH)
        print(f"Loaded {len(df)} rows.")
        
        # 3. Buat Konten Utama
        df['page_content'] = (
            "Judul: " + df['title'].fillna('') + 
            "\nAbstrak: " + df['abstract'].fillna('')
        )
        
        loader = DataFrameLoader(df, page_content_column="page_content")
        documents = loader.load()

        # Update Metadata
        metadata_cols = ['title', 'authors', 'keywords', 'uri', 'abstract'] 
        for i, doc in enumerate(documents):
            row_data = df.iloc[i]
            doc_metadata = {}
            for col in metadata_cols:
                val = row_data.get(col, '')
                doc_metadata[col] = str(val) if pd.notna(val) else ''
            doc.metadata = doc_metadata
        
        print(f"Metadata attached to {len(documents)} docs.")
        
        # --- LOGIKA CHECKPOINT ---
        start_index = 0
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, "r") as f:
                try:
                    content = f.read().strip()
                    if content:
                        start_index = int(content)
                        print(f"Resuming from chunk index: {start_index}")
                except:
                    start_index = 0

        # 5. Split Dokumen
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
        texts = text_splitter.split_documents(documents)
        print(f"Total chunks: {len(texts)}")
        
        if start_index >= len(texts):
            print("All documents indexed!")
            return True
        
        # 6. Inisialisasi Chroma
        # Pastikan folder target dibuat
        os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
        
        db_client = chromadb.PersistentClient(path=VECTOR_STORE_PATH)
        
        if start_index == 0:
            try:
                db_client.delete_collection(name=COLLECTION_NAME)
                print(f"Deleted existing collection: {COLLECTION_NAME} (Fresh Start)")
            except:
                pass 
        else:
            print(f"Appending to existing collection (starting from {start_index}).")
        
        vector_store = Chroma(client=db_client, collection_name=COLLECTION_NAME, embedding_function=embeddings)
        
        # 7. Batch Processing
        batch_size = 100
        total_chunks = len(texts)
        max_retries = 3 
        
        print(f"Indexing to {VECTOR_STORE_PATH}...")
        
        try:
            for i in range(start_index, total_chunks, batch_size):
                batch = texts[i : i + batch_size]
                
                for attempt in range(max_retries):
                    try:
                        vector_store.add_documents(documents=batch)
                        
                        next_index = min(i + batch_size, total_chunks)
                        with open(CHECKPOINT_FILE, "w") as f:
                            f.write(str(next_index))
                        
                        print(f"Batch {i} - {next_index} saved.")
                        time.sleep(0.5)
                        break 
                    except Exception as e:
                        print(f"Error batch {i} (Attempt {attempt+1}): {e}")
                        if attempt < max_retries - 1:
                            time.sleep(5 * (attempt + 1))
                        else:
                            print(f"SKIP batch {i}.")
                            with open("failed_batches.log", "a") as f:
                                f.write(f"Batch {i}: {e}\n")

        except KeyboardInterrupt:
            print("\nSTOPPED BY USER.")
            return False

        print("\nIndexing Complete.")
        return True
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        return False

if __name__ == "__main__":
    success = run_indexing()
    if not success:
        sys.exit(1)