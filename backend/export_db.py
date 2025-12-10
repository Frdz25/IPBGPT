import pandas as pd
import os
import psycopg2
import paramiko 
import sys
from sshtunnel import SSHTunnelForwarder 
from dotenv import load_dotenv

# Muat variabel lingkungan
load_dotenv()

# --- KONFIGURASI DATABASE ---
DB_HOST = os.environ.get("DB_HOST") 
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))

# --- KONFIGURASI SSH (Opsional) ---
SSH_HOST = os.environ.get("SSH_HOST")      
SSH_USER = os.environ.get("SSH_USER")
SSH_KEY_PATH = os.environ.get("SSH_KEY_PATH") 
SSH_PASSWORD = os.environ.get("SSH_PASSWORD")
SSH_PORT = int(os.environ.get("SSH_PORT", "22"))

# --- KONFIGURASI FILE ---
# Path Absolut di dalam container (/app/data_source/...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_SOURCE_DIR = os.path.join(BASE_DIR, "data_source")
CSV_FILENAME = "paper_metadata.csv"
LOCAL_EXPORT_PATH = os.path.join(DATA_SOURCE_DIR, CSV_FILENAME)

QUERY = "SELECT * FROM paper_metadata" 
LOCAL_BIND_PORT = 6543 

def get_db_connection():
    """
    Membuat koneksi database, otomatis memilih antara SSH Tunnel atau Direct.
    """
    if SSH_HOST:
        print(f"Mode: SSH Tunnel via {SSH_HOST}...")
        
        ssh_pkey = None
        if SSH_KEY_PATH and os.path.exists(SSH_KEY_PATH):
            try:
                # Coba load sebagai RSA
                ssh_pkey = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
            except Exception:
                try:
                    # Fallback ke Ed25519 jika bukan RSA
                    ssh_pkey = paramiko.Ed25519Key.from_private_key_file(SSH_KEY_PATH)
                except Exception as e:
                    print(f"Warning: Gagal load SSH Key: {e}")
        
        # Setup Tunnel dengan Parameter Anti-Error DSSKey
        tunnel = SSHTunnelForwarder(
            (SSH_HOST, SSH_PORT), 
            ssh_username=SSH_USER,
            ssh_pkey=ssh_pkey,
            ssh_password=SSH_PASSWORD,
            remote_bind_address=(DB_HOST, DB_PORT),
            local_bind_address=('127.0.0.1', LOCAL_BIND_PORT),
            # --- FIX PENTING ---
            # Mencegah sshtunnel mencari key lama di sistem yang menyebabkan error DSSKey
            host_pkey_directories=[], 
            ssh_private_key_password=None,
        )
        tunnel.start()
        print(f"SSH Tunnel established.")
        
        conn = psycopg2.connect(
            host='127.0.0.1',
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=tunnel.local_bind_port[1]
        )
        return conn, tunnel

    else:
        print(f"Mode: Direct Connection to {DB_HOST}...")
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn, None

def extract_and_save_locally():
    conn = None
    tunnel = None
    try:
        # Pastikan folder tujuan ada
        if not os.path.exists(DATA_SOURCE_DIR):
            print(f"Creating directory: {DATA_SOURCE_DIR}")
            os.makedirs(DATA_SOURCE_DIR, exist_ok=True)

        conn, tunnel = get_db_connection()
        print("Connected to database.")
        
        print("Extracting data...")
        df = pd.read_sql(QUERY, conn)
        print(f"Extracted {len(df)} rows.")
        
        df.to_csv(LOCAL_EXPORT_PATH, index=False, encoding='utf-8', sep=',') 
        print(f"Data saved to {LOCAL_EXPORT_PATH}")
        return True

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        return False
        
    finally:
        if conn: conn.close()
        if tunnel: tunnel.stop()

if __name__ == "__main__":
    success = extract_and_save_locally()
    if not success:
        sys.exit(1)