import streamlit as st
from ui_components import initialize_session_state, display_sidebar, display_chat_interface, display_mode_toggle
from app_modes import display_just_chat_interface

def main():

    st.set_page_config(
        page_title="IPB-GPT",
        page_icon="frontend/img/logo.png",
        layout="wide"
    )

    hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    st.title("💬 IPB-GPT")
    st.caption("🚀 IPB Research Assistant: A Smart Chatbot to Help You Find Relevant Research for Your Undergraduate Thesis. Chat About Research at IPB Anytime!")

    initialize_session_state()
    display_mode_toggle()

    if st.session_state['mode'] == "Chat Mode":
        display_just_chat_interface()
    else:
        display_sidebar()
        display_chat_interface()

if __name__ == "__main__":
    main()
