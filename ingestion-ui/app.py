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
    st.subheader("Ajouter des Documents")
    uploaded_files = st.file_uploader("Choisir des fichiers PDF", type=["pdf"], accept_multiple_files=True)
    level = st.selectbox("Cible du document", ["level1", "level2"], format_func=lambda x: "Niveau 1 (Public/Élèves)" if x == "level1" else "Niveau 2 (Interne/Direction)")
    
    if st.button("Ingérer les documents"):
        if uploaded_files:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Traitemement de {uploaded_file.name} ({i+1}/{len(uploaded_files)})...")
                try:
                    # Reset pointer to ensured it is read from start if streamlit implies re-reads (safe practice)
                    uploaded_file.seek(0)
                    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                    data = {"level": level}
                    response = requests.post(f"{BACKEND_URL}/ingest", files=files, data=data)
                    
                    if response.status_code == 200:
                        st.toast(f"✅ {uploaded_file.name} ingéré !")
                    else:
                        st.error(f"❌ Erreur pour {uploaded_file.name}: {response.text}")
                except Exception as e:
                    st.error(f"❌ Erreur de connexion pour {uploaded_file.name}: {e}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            status_text.text("Opération terminée !")
            st.success(f"Traitement de {len(uploaded_files)} fichiers terminé.")
        else:
            st.error("Veuillez sélectionner au moins un fichier.")

with col2:
    st.subheader("Maintenance")
    st.error("Zone de Danger")
    if st.button("Effacer TOUTE la collection Niveau 1", type="primary"):
        st.error("Fonctionnalité non implémentée pour sécurité.")
    
    if st.button("Effacer TOUTE la collection Niveau 2", type="primary"):
        st.error("Fonctionnalité non implémentée pour sécurité.")
