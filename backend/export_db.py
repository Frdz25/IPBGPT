import pandas as pd
import psycopg2
import paramiko 
import os
import sys
from sshtunnel import SSHTunnelForwarder 
from dotenv import load_dotenv

# Muat variabel lingkungan untuk kredensial DB
load_dotenv()

# --- KONFIGURASI DATABASE (Ambil dari .env) ---
DB_HOST = os.environ.get("DB_HOST") # Host DB tujuan (target)
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))

# --- KONFIGURASI SSH/TUNNEL ---
SSH_HOST = os.environ.get("SSH_HOST")           # Bastion/Jump Host
SSH_USER = os.environ.get("SSH_USER")
SSH_PASSWORD = os.environ.get("SSH_PASSWORD") 
SSH_KEY_PATH = os.environ.get("SSH_KEY_PATH")   # Path ke kunci SSH
SSH_PORT = int(os.environ.get("SSH_PORT", "22"))

# --- KONFIGURASI FILE ---
# BASE_DIR = /app (tempat script berada)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Target: /data_source (Naik satu level dari /app)
# Di Docker, ini akan mengarah ke folder volume yang baru kita mount
DATA_SOURCE_DIR = os.path.join(BASE_DIR, "..", "data_source")

CSV_FILENAME = "paper_metadata.csv"
LOCAL_EXPORT_PATH = os.path.join(DATA_SOURCE_DIR, CSV_FILENAME)

QUERY = "SELECT * FROM metadata_paper" 
LOCAL_BIND_PORT = 6543 # Port lokal yang akan diteruskan (forwarded)

if not hasattr(paramiko, "DSSKey"):
    class DSSKey:
        pass
    paramiko.DSSKey = DSSKey

def extract_and_save_locally():
    print("--- Starting Database Extraction with SSH Tunnel ---")
    
    # 1. Mulai SSH Tunnel
    try:
        # Pengecekan Kunci SSH
        ssh_pkey = None
        if SSH_KEY_PATH and os.path.exists(SSH_KEY_PATH):
            try:
                ssh_pkey = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
            except Exception as e:
                print(f"WARNING: Failed to load SSH Key: {e}. Falling back to password.")
                ssh_pkey = None
        else:
            # print("WARNING: SSH key path not found or empty. Using password auth.")
            pass

        with SSHTunnelForwarder(
            (SSH_HOST, SSH_PORT), 
            ssh_username=SSH_USER,
            ssh_pkey=ssh_pkey,        # Kunci (bisa None)
            ssh_password=SSH_PASSWORD,      
            remote_bind_address=(DB_HOST, DB_PORT),
            local_bind_address=('127.0.0.1', LOCAL_BIND_PORT)
        ) as tunnel:
            
            print(f"SSH Tunnel opened. Local port: {tunnel.local_bind_port}")
            
            # 2. Ekstraksi Data dari Database melalui Tunnel
            conn = psycopg2.connect(
                host='127.0.0.1', # Koneksi ke port lokal
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=tunnel.local_bind_port # Gunakan port lokal yang diteruskan
            )
            
            print("Connected. Starting data extraction in chunks...")
            
            # Tentukan ukuran chunk (misal 5000 baris per tarikan)
            chunk_size = 5000
            offset = 0
            first_chunk = True
            
            # Gunakan iterator chunksize dari pandas
            for chunk in pd.read_sql(QUERY, conn, chunksize=chunk_size):
                # Mode 'w' untuk chunk pertama (write/overwrite), 'a' untuk selanjutnya (append)
                mode = 'w' if first_chunk else 'a'
                header = first_chunk # Tulis header hanya di awal
                
                # Simpan bertahap ke CSV
                chunk.to_csv(LOCAL_EXPORT_PATH, index=False, mode=mode, header=header)
                
                offset += len(chunk)
                print(f"Saved {len(chunk)} rows (Total: {offset})...")
                first_chunk = False
            
            conn.close()
            print(f"Successfully extracted {len(df)} rows.")

    except paramiko.ssh_exception.AuthenticationException:
        print("FATAL ERROR: SSH Authentication failed. Check SSH key and user.")
        return False
    except paramiko.ssh_exception.NoValidConnectionsError as e:
        print(f"FATAL ERROR: Could not connect to SSH host {SSH_HOST}. {e}")
        return False
    except Exception as e:
        print(f"FATAL ERROR during database connection/extraction: {e}")
        return False

    # 3. Simpan DataFrame ke File CSV Lokal
    try:
        print(f"Saving data to CSV locally at {LOCAL_EXPORT_PATH}...")
        os.makedirs(os.path.dirname(LOCAL_EXPORT_PATH), exist_ok=True)
        df.to_csv(LOCAL_EXPORT_PATH, index=False, encoding='utf-8', sep=',') 
        print(f"Data saved locally to {LOCAL_EXPORT_PATH}")
        return True

    except Exception as e:
        print(f"FATAL ERROR saving CSV: {e}")
        return False

if __name__ == "__main__":
    success = extract_and_save_locally()
    if not success:
        sys.exit(1)