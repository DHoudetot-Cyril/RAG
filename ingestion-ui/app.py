import streamlit as st
import requests
import os

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
st.set_page_config(page_title="RAG École - Ingestion", page_icon="📥")

st.title("📥 Ingestion de Documents")

st.warning("⚠️ Zone Réservée au Secrétariat et à la Direction")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Ajouter un Document")
    uploaded_file = st.file_uploader("Choisir un fichier PDF", type=["pdf"])
    level = st.selectbox("Niveau d'accès", ["level1", "level2"], format_func=lambda x: "Niveau 1 (Élève)" if x == "level1" else "Niveau 2 (Direction)")
    
    if st.button("Ingérer le document"):
        if uploaded_file is not None:
            with st.spinner("Envoi en cours..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                    data = {"level": level}
                    response = requests.post(f"{BACKEND_URL}/ingest", files=files, data=data)
                    
                    if response.status_code == 200:
                        st.success(f"Document ingéré avec succès dans {level} !")
                    else:
                        st.error(f"Erreur: {response.text}")
                except Exception as e:
                    st.error(f"Erreur de connexion: {e}")
        else:
            st.error("Veuillez sélectionner un fichier.")

with col2:
    st.subheader("Maintenance")
    st.danger("Zone de Danger")
    if st.button("Effacer TOUTE la collection Niveau 1", type="primary"):
        st.error("Fonctionnalité non implémentée pour sécurité.")
    
    if st.button("Effacer TOUTE la collection Niveau 2", type="primary"):
        st.error("Fonctionnalité non implémentée pour sécurité.")
