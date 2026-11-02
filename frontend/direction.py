"""Interface Direction : chat sur tous les niveaux + consultation de la base documentaire."""

import pandas as pd
import streamlit as st

from api_client import ApiError
from ui import LEVEL_LABELS, new_conversation_button, render_chat, setup_page

client = setup_page("Direction", "🏢", "DIRECTION_API_KEY")

st.title("🏢 Espace Direction")

SCOPES = {
    "Tous les documents (niveaux 1 + 2)": None,
    "Vue élève (niveau 1 seulement)": ["level1"],
    "Documents internes (niveau 2 seulement)": ["level2"],
}

with st.sidebar:
    st.markdown("### Périmètre de recherche")
    scope_label = st.radio("Rechercher dans", list(SCOPES), label_visibility="collapsed")
    st.caption("La « vue élève » permet de vérifier exactement ce que voient les élèves.")
new_conversation_button("direction_messages")

chat_tab, docs_tab = st.tabs(["💬 Assistant", "📚 Base documentaire"])

with chat_tab:
    render_chat(client, "direction_messages", levels=SCOPES[scope_label], placeholder="Rechercher une information…")

with docs_tab:
    try:
        documents = client.documents()
    except ApiError as exc:
        st.error(str(exc))
        documents = []

    if not documents:
        st.info("Aucun document indexé pour le moment.")
    else:
        df = pd.DataFrame(documents)
        df["Niveau"] = df["level"].map(LEVEL_LABELS)
        df["Ingéré le"] = pd.to_datetime(df["ingested_at"]).dt.strftime("%d/%m/%Y %H:%M")
        col1, col2, col3 = st.columns(3)
        col1.metric("Documents", len(df))
        col2.metric("Niveau 1", int((df["level"] == "level1").sum()))
        col3.metric("Niveau 2", int((df["level"] == "level2").sum()))
        search = st.text_input("🔎 Filtrer par nom")
        if search:
            df = df[df["document"].str.contains(search, case=False, regex=False)]
        st.dataframe(
            df[["document", "Niveau", "file_type", "chunks", "Ingéré le"]].rename(
                columns={"document": "Document", "file_type": "Type", "chunks": "Passages"}
            ),
            hide_index=True,
            use_container_width=True,
        )
