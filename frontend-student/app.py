import streamlit as st
import requests
import os

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
st.set_page_config(page_title="RAG Administration - Élève", page_icon="ℹ️")

st.title("ℹ️ Assistant Administratif")

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Une question sur les stages, le règlement, les dates ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            response = requests.post(f"{BACKEND_URL}/chat/student", json={"message": prompt, "level": "level1"})
            if response.status_code == 200:
                data = response.json()
                st.markdown(data["response"])
                st.caption(f"Source: {data['source']}")
                st.session_state.messages.append({"role": "assistant", "content": data["response"]})
            else:
                st.error(f"Erreur: {response.text}")
        except Exception as e:
            st.error(f"Erreur de connexion: {e}")
