import streamlit as st
import requests
import os

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
st.set_page_config(page_title="RAG Administration - Ingestion", page_icon="📥", layout="wide")

st.title("📥 Ingestion de Documents")
st.warning("⚠️ Zone Réservée au Secrétariat et à la Direction")

# ─── Section 1: Upload & Maintenance ─────────────────────────────────────────
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
            st.rerun()
        else:
            st.error("Veuillez sélectionner au moins un fichier.")

with col2:
    st.subheader("Maintenance")
    st.error("Zone de Danger")
    if st.button("Effacer TOUTE la collection Niveau 1", type="primary"):
        st.error("Fonctionnalité non implémentée pour sécurité.")
    
    if st.button("Effacer TOUTE la collection Niveau 2", type="primary"):
        st.error("Fonctionnalité non implémentée pour sécurité.")

# ─── Section 2: Documents ingérés par collection ──────────────────────────────
st.divider()
st.subheader("📚 Documents Ingérés par Collection")

col_refresh = st.columns([1, 5])
with col_refresh[0]:
    refresh = st.button("🔄 Actualiser")

try:
    response = requests.get(f"{BACKEND_URL}/documents", timeout=10)
    if response.status_code == 200:
        docs = response.json()
        
        tab1, tab2 = st.tabs(["📗 Niveau 1 – Public / Élèves", "📕 Niveau 2 – Interne / Direction"])
        
        with tab1:
            level1_docs = docs.get("level1", [])
            if level1_docs:
                st.info(f"**{len(level1_docs)} document(s)** dans la base publique.")
                st.dataframe(
                    [{"📄 Document": d["source"], "🔢 Chunks": d["chunks"]} for d in level1_docs],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("Aucun document dans la base Niveau 1.")
        
        with tab2:
            level2_docs = docs.get("level2", [])
            if level2_docs:
                st.info(f"**{len(level2_docs)} document(s)** dans la base interne.")
                st.dataframe(
                    [{"📄 Document": d["source"], "🔢 Chunks": d["chunks"]} for d in level2_docs],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("Aucun document dans la base Niveau 2.")
    else:
        st.error(f"Impossible de récupérer les documents: {response.status_code}")
except Exception as e:
    st.error(f"Erreur de connexion au backend: {e}")
