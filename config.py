import streamlit as st
from google import genai

def get_gemini_client() -> genai.Client:
    """
    Streamlit Secrets에서 GEMINI_API_KEY를 읽어와 SDK Client를 생성합니다.
    """
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        return genai.Client(api_key=api_key)
    except Exception:
        st.error("⚠️ GEMINI_API_KEY가 설정되지 않았습니다. .streamlit/secrets.toml을 확인해 주세요.")
        st.stop()
