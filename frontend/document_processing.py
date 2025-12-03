import requests
import os
from dotenv import load_dotenv

load_dotenv()

URL_BASE = os.getenv("URL_BASE")

def upload_pdf(file):
    try:
        url = f"{URL_BASE}/upload-pdf/"
        
        # 1. Reset pointer file ke awal 
        file.seek(0)
        
        # 2. Gunakan format Tuple eksplisit: (filename, file_object, content_type)
        files = {'file': (file.name, file, "application/pdf")}
        
        response = requests.post(url, files=files)
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        return {"error": f"Server Error ({response.status_code}): {response.text}"}
    
    except requests.RequestException:
        return {"error": "Failed to connect to the backend server. Is the FastAPI server running?"}


def get_related_documents(title, number):
    try:
        url = f"{URL_BASE}/related_documents/"
        data = {"title": title, "number":number}
        response = requests.post(url, json=data)
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.HTTPError as e:
        return {"error": f"Server Error ({response.status_code}): {response.text}"}
    
    except requests.RequestException:
        return {"error": "Failed to get related documents. Server might be busy or unavailable."}