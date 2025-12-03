import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

URL_BASE = os.getenv("URL_BASE")

def process_pdf_chat(prompt, chat_history):
    session_id = st.session_state.get('session_id')
    if not session_id:
        return "Error: No active PDF session found. Please re-upload the PDF."
        
    url = f"{URL_BASE}/chat-with-pdf/"
    data = {
        "query": prompt,
        "chat_history": chat_history,
        "session_id": session_id 
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            return result.get('response', 'An unknown error occurred.')
        else:
            return f"Failed to process chat. Server responded with {response.status_code}: {response.text}"
    except requests.RequestException:
        return "Failed to process chat. Server might be busy or unavailable."

def process_selected_documents_chat(prompt, chat_history):
    if not st.session_state['selected_document']:
        return "Error: No documents selected."
    
    context = "\n\n".join(f"{doc['judul']} {doc['abstrak']} {doc['url']}" for doc in st.session_state['selected_document'])

    url = f"{URL_BASE}/chat/"
    data = {
        "query": prompt,
        "context": context,
        "chat_history": chat_history,
        "session_id": st.session_state['session_id'] 
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            return result.get('response', 'An unknown error occurred.')
        else:
            return f"Failed to process chat. Server responded with {response.status_code}: {response.text}"
    except requests.RequestException:
        return "Failed to process chat. Server might be busy or unavailable."