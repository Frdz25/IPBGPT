from document_processing import upload_pdf, get_related_documents
from chat_logic import process_pdf_chat, process_selected_documents_chat
from dotenv import load_dotenv
import streamlit as st
import re
import os

load_dotenv()

API_URL = os.getenv("URL_BASE")
def initialize_session_state():
    defaults = {
        'messages': [{"role": "assistant", "content": "Can I assist you today?"}],
        'related_document': None,
        'selected_document': [],
        'document_chat': None,
        'number': 5,
        'prompt': None,
        'uploaded_file': None,
        'current_file': None,
        'mode': 'Search and Chat',
        'previous_mode': 'Search and Chat',
        'session_id': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def display_mode_toggle():
    col1, col2 = st.columns([9, 1])
    with col1:
        if st.button("Clear Chat"):
            st.session_state.clear_chat = True
            st.session_state.messages = [{"role": "assistant", "content": "Chat cleared. How can I assist you?"}]
    
    with col2:
        if 'mode_toggle' not in st.session_state:
            st.session_state['mode_toggle'] = st.session_state['mode'] == "Chat Mode"
        
        toggle = st.toggle("chat mode", key="mode_toggle", value=st.session_state['mode_toggle'])
        new_mode = "Chat Mode" if toggle else "Search and Chat"
        
        if new_mode != st.session_state['previous_mode']:
            st.session_state['mode'] = new_mode
            st.session_state['previous_mode'] = new_mode
            st.session_state.messages = [{"role": "assistant", "content": f"Mode changed to {new_mode}. How can I assist you?"}]


def display_sidebar():
    with st.sidebar:
        st.title("FIND RELATED RESEARCH📄")
        
        text_input = st.text_input("Enter your undergraduate thesis Topic 👇")
        
        new_number = st.number_input(
            'Max number of research to display', 
            min_value=1, 
            max_value=20, 
            format='%i', 
            value=st.session_state['number']
        )
        
        search_button = st.button("Search for Related Documents")

        if search_button or new_number != st.session_state['number'] or text_input != st.session_state.get('prompt', ''):
            if text_input:
                st.session_state['number'] = new_number
                st.session_state['prompt'] = text_input
                
                with st.spinner("Searching for related documents..."):
                    related_docs = get_related_documents(text_input, new_number)

                if not isinstance(related_docs, dict):
                    st.error("Unexpected response from backend.")
                    st.session_state['related_document'] = None
                    return
                
                if 'error' in related_docs:
                    st.error(related_docs['error'])
                    st.session_state['related_document'] = None
                else:
                    st.session_state['related_document'] = related_docs
                    st.session_state['selected_document'] = []
                    st.success(f"Related Documents Found!")

        display_retrieved_documents()

    return text_input

def display_retrieved_documents():
    related = st.session_state.get('related_document')

    if not related or not isinstance(related, dict):
        return

    st.subheader("Retrieved Documents") 
    
    if 'related_documents' not in related:
        st.warning("No related documents found in the response structure.")
        return

    docs = related['related_documents']

    if not isinstance(docs, list):
        st.warning("Invalid document list received.")
        return
        
    pdf_is_uploaded = st.session_state.get('uploaded_file') is not None

    if pdf_is_uploaded:
        st.warning('Clear the PDF first to select documents from the search results.')


    for i, doc in enumerate(docs):
        # Tambahkan pemisah visual yang lebih jelas
        st.markdown(f"**Result {i+1}**") 
        
        # Tampilkan detail dokumen
        st.markdown(f"**Judul**: {doc['judul']}")
        st.markdown(f"**URL**: [{doc['url']}]({doc['url']})")
        
        # Logika Checkbox (Hanya aktif jika tidak ada PDF diunggah)
        if not pdf_is_uploaded:
            checkbox_key = f"checkbox_search_{i}" # Gunakan key unik agar tidak bentrok
            if st.checkbox(f"Select Document {i+1} for Chat", key=checkbox_key):
                if doc not in st.session_state['selected_document']:
                    st.session_state['selected_document'].append(doc)
            else:
                if doc in st.session_state['selected_document']:
                    st.session_state['selected_document'].remove(doc)
        
        #st.markdown("---") # Hapus ini karena sudah ada di atas


def render_llm_response(response):

    segments = re.split(r'(```[\s\S]*?```)', response)
    
    for segment in segments:
        if segment.startswith('```') and segment.endswith('```'):
            code = segment.strip('`').split('\n')
            language = code[0] if code[0] else 'python'  
            code_content = '\n'.join(code[1:])
            st.code(code_content, language=language)
        else:
            st.markdown(segment)

def display_chat_interface():

    if not st.session_state['selected_document']:
        st.session_state['uploaded_file'] = st.file_uploader("Choose a PDF")
    
    # Cek apakah file yang diunggah berubah atau baru
    if st.session_state.get('current_file') != st.session_state['uploaded_file']:
        if st.session_state['uploaded_file']:
            with st.spinner("Processing uploaded PDF. Please wait..."):
                # Kirim file untuk diunggah dan diproses
                result = upload_pdf(st.session_state['uploaded_file'])
                
                if 'error' in result:
                    st.error(result['error'])
                    st.session_state['current_file'] = None
                    st.session_state['session_id'] = None
                else:
                    st.session_state['current_file'] = st.session_state['uploaded_file']
                    # Simpan session_id yang dikembalikan oleh backend
                    st.session_state['session_id'] = result.get('session_id') 
                    st.success("PDF processed successfully!")
        elif st.session_state.get('current_file') is not None:
             # File dihapus oleh user, reset state
            st.session_state['current_file'] = None
            st.session_state['session_id'] = None
            st.session_state.messages = [{"role": "assistant", "content": "PDF cleared. How can I assist you?"}]

    # Tentukan apakah chat harus diaktifkan dan apakah sudah siap (untuk PDF)
    chat_enabled = st.session_state['uploaded_file'] is not None or st.session_state['selected_document']
    
    # Tambahkan pemeriksaan kondisi kesiapan PDF
    pdf_ready = not st.session_state['uploaded_file'] or (st.session_state['uploaded_file'] and st.session_state.get('session_id'))
    
    # Nonaktifkan chat input jika chat diaktifkan tetapi PDF belum siap (session_id missing)
    chat_input_disabled = chat_enabled and not pdf_ready

    if chat_enabled:
        if prompt := st.chat_input("Type your message here...", disabled=chat_input_disabled):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.spinner("Thinking..."):
                chat_history = [{"role": msg["role"], "content": msg["content"]} for msg in st.session_state.messages]
                if st.session_state['uploaded_file']:
                    # --- PERBAIKAN: Hapus argumen ketiga (pdf_text) ---
                    response = process_pdf_chat(prompt, chat_history) 
                elif st.session_state['selected_document']:
                    response = process_selected_documents_chat(prompt, chat_history)
                
                if response.startswith("Failed to") or response.startswith("Error: No active PDF session"):
                    st.error(response)
                else:
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_llm_response(message["content"])
            else:
                st.markdown(message["content"])

    if st.session_state['uploaded_file']:
        session_id_val = st.session_state.get('session_id')
        display_id = str(session_id_val)[:8] if session_id_val else 'N/A'
        
        # Tambahkan pesan untuk menunggu proses jika session_id masih kosong
        if not session_id_val and st.session_state['current_file']:
             st.warning("PDF processing in progress... Please wait until 'PDF processed successfully' appears.")
        
        st.info(f"You are currently chatting with the uploaded PDF.")
    elif st.session_state['selected_document']:
        st.info("You are currently chatting with the selected documents from the search results.")
    elif st.session_state['mode'] == "Chat Mode":
        st.info("You are in Chat Mode mode.")