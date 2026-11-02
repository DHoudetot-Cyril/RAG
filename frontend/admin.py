"""Interface d'administration : ingestion, suivi et suppression des documents."""

import pandas as pd
import streamlit as st

from api_client import ApiError
from ui import LEVEL_LABELS, health_sidebar, setup_page

client = setup_page("Administration", "📥", "ADMIN_API_KEY")

st.title("📥 Gestion documentaire")
st.warning("Zone réservée au secrétariat et à la direction.")
health_sidebar(client)

STATUS_LABELS = {"ingested": "✅ ajouté", "updated": "🔄 mis à jour", "unchanged": "⏭️ inchangé"}

# --------------------------------------------------------------------- upload
st.subheader("Ajouter des documents")
with st.form("upload", clear_on_submit=True):
    files = st.file_uploader(
        "Formats acceptés : PDF, Word (.docx), PowerPoint (.pptx), texte, Markdown",
        type=["pdf", "docx", "pptx", "txt", "md"],
        accept_multiple_files=True,
    )
    level = st.radio(
        "Niveau d'accès",
        ["level1", "level2"],
        format_func=lambda lvl: {
            "level1": "Niveau 1 — visible par les élèves et la direction",
            "level2": "Niveau 2 — visible uniquement par la direction",
        }[lvl],
        horizontal=True,
    )
    submitted = st.form_submit_button("Ingérer", type="primary")

if submitted:
    if not files:
        st.error("Sélectionnez au moins un fichier.")
    else:
        results = []
        progress = st.progress(0.0, text="Ingestion…")
        for i, uploaded in enumerate(files, start=1):
            progress.progress((i - 1) / len(files), text=f"{uploaded.name} ({i}/{len(files)})…")
            try:
                body = client.upload(uploaded.name, uploaded.getvalue(), level)
                results.append(
                    {"Fichier": uploaded.name, "Statut": STATUS_LABELS[body["status"]], "Passages": body["chunks"]}
                )
            except ApiError as exc:
                results.append({"Fichier": uploaded.name, "Statut": f"❌ {exc}", "Passages": 0})
        progress.progress(1.0, text="Terminé")
        st.dataframe(pd.DataFrame(results), hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ catalogue
st.divider()
st.subheader("📚 Documents indexés")
try:
    documents = client.documents()
except ApiError as exc:
    st.error(str(exc))
    st.stop()

for lvl, tab in zip(["level1", "level2"], st.tabs([LEVEL_LABELS["level1"], LEVEL_LABELS["level2"]]), strict=True):
    with tab:
        docs = [d for d in documents if d["level"] == lvl]
        if not docs:
            st.info("Aucun document dans ce niveau.")
            continue
        st.caption(f"{len(docs)} document(s), {sum(d['chunks'] for d in docs)} passages indexés.")
        for doc in docs:
            col_name, col_meta, col_action = st.columns([5, 3, 2])
            col_name.markdown(f"📄 **{doc['document']}**")
            col_meta.caption(f"{doc['file_type'].upper()} · {doc['chunks']} passages")
            confirm_key = f"confirm-{lvl}-{doc['document_id']}"
            if st.session_state.get(confirm_key):
                if col_action.button("Confirmer", key=f"yes-{confirm_key}", type="primary"):
                    try:
                        client.delete(lvl, doc["document_id"])
                        st.toast(f"{doc['document']} supprimé.")
                    except ApiError as exc:
                        st.error(str(exc))
                    st.session_state[confirm_key] = False
                    st.rerun()
            elif col_action.button("🗑️ Supprimer", key=f"del-{confirm_key}"):
                st.session_state[confirm_key] = True
                st.rerun()
