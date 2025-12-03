import pandas as pd
import psycopg2
import paramiko 
import os
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
SSH_HOST = os.environ.get("SSH_HOST")      # Bastion/Jump Host
SSH_USER = os.environ.get("SSH_USER")
SSH_KEY_PATH = os.environ.get("SSH_KEY_PATH") # Path ke kunci SSH
SSH_PORT = int(os.environ.get("SSH_PORT", "22"))

# --- KONFIGURASI FILE ---
CSV_FILENAME = "paper_metadata.csv"
LOCAL_EXPORT_PATH = f"../data_source/{CSV_FILENAME}" 
QUERY = "SELECT * FROM paper_metadata" 

# Port Lokal yang akan digunakan untuk tunneling
LOCAL_BIND_PORT = 6543 # Port lokal yang akan diteruskan (forwarded)

def extract_and_save_locally():
    print("--- Starting Database Extraction with SSH Tunnel ---")
    
    # 1. Mulai SSH Tunnel
    try:
        # Pengecekan Kunci SSH: Jika menggunakan file kunci
        if SSH_KEY_PATH and os.path.exists(SSH_KEY_PATH):
            ssh_pkey = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
        else:
            # Jika tidak ada kunci, coba koneksi menggunakan password (kurang disarankan)
            ssh_pkey = None
            print("WARNING: SSH key not found. Trying password auth (if configured).")
            # Jika tidak menggunakan kunci, Anda mungkin perlu menambahkan konfigurasi password 
            # atau menggunakan Agent forwarding. Namun, kita fokus pada kunci.

        # Menggunakan SSHTunnelForwarder untuk mengelola tunneling
        with SSHTunnelForwarder(
            (SSH_HOST, SSH_PORT), 
            ssh_username=SSH_USER,
            ssh_pkey=ssh_pkey,
            remote_bind_address=(DB_HOST, DB_PORT),
            local_bind_address=('127.0.0.1', LOCAL_BIND_PORT)
        ) as tunnel:
            
            print(f"SSH Tunnel opened. Local port: {tunnel.local_bind_port[1]}")
            
            # 2. Ekstraksi Data dari Database melalui Tunnel
            conn = psycopg2.connect(
                host='127.0.0.1', # Koneksi ke port lokal
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=tunnel.local_bind_port[1] # Gunakan port lokal yang diteruskan
            )
            print("Connected to database successfully (via tunnel).")
            
            df = pd.read_sql(QUERY, conn)
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
        os.makedirs(os.path.dirname(LOCAL_EXPORT_PATH), exist_ok=True)
        df.to_csv(LOCAL_EXPORT_PATH, index=False, encoding='utf-8', sep=',') 
        print(f"Data saved locally to {LOCAL_EXPORT_PATH}")
        return True

    except Exception as e:
        print(f"FATAL ERROR saving CSV: {e}")
        return False

if __name__ == "__main__":
    # Peringatan: Pastikan Anda telah menginstal paramiko dan sshtunnel
    if not os.environ.get("SSH_HOST"):
        print("ERROR: SSH_HOST is not configured in .env. Falling back to direct connection.")
        # Jika SSH tidak dikonfigurasi, Anda dapat menambahkan fallback ke koneksi langsung 
        # tanpa tunnel di sini, tetapi untuk tugas ini, kita asumsikan SSH diperlukan.
        # Alternatif: exit 1

    extract_and_save_locally()