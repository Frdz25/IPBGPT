import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("URL_BASE")
QUERY_ENDPOINT = f"{API_URL}/combined-query-chat/"


def display_just_chat_interface():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What would you like to know?"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        chat_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in st.session_state.messages
        ]

        with st.spinner("Thinking..."):
            response = requests.post(
                QUERY_ENDPOINT,
                json={
                    "query": prompt, 
                    "chat_history": chat_history,
                    "session_id": st.session_state['session_id']
                }
            )

        if response.status_code == 200:
            answer = response.json()["response"]
            
            with st.chat_message("assistant"):
                st.markdown(answer)
                
            st.session_state.messages.append({"role": "assistant", "content": answer})
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
