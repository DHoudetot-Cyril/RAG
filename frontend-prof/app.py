import streamlit as st
import requests
import os

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
st.set_page_config(page_title="RAG Administration - Direction", page_icon="🏢", layout="wide")

st.title("🏢 Espace Direction")

tab1, tab2 = st.tabs(["💬 Chat & Vérification", "📚 Base Documentaire"])

with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Paramètres")
        level_access = st.radio("Niveau de recherche", ["level1", "level2"], format_func=lambda x: "Niveau 1 (Public/Élèves)" if x == "level1" else "Niveau 2 (Interne/Direction)")
    
    with col2:
        st.subheader("Chat")
        if "prof_messages" not in st.session_state:
            st.session_state.prof_messages = []

        for message in st.session_state.prof_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Rechercher une info..."):
            st.session_state.prof_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    response = requests.post(f"{BACKEND_URL}/chat/prof", json={"message": prompt, "level": level_access})
                    if response.status_code == 200:
                        data = response.json()
                        st.markdown(data["response"])
                        st.info(f"Source: {data['source']} (Accès: {level_access})")
                        st.session_state.prof_messages.append({"role": "assistant", "content": data["response"]})
                    else:
                        st.error(f"Erreur: {response.text}")
                except Exception as e:
                    st.error(f"Erreur de connexion: {e}")

with tab2:
    st.header("Explorateur de Documents")
    st.write("Liste des documents ingérés (Connecté à Qdrant)")
    # Placeholder for doc listing
