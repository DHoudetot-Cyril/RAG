"""Interface Élève : chat sur les documents publics (niveau 1) uniquement."""

import streamlit as st

from ui import new_conversation_button, render_chat, setup_page

client = setup_page("Élève", "🎓", "STUDENT_API_KEY")

st.title("🎓 Assistant administratif")
st.caption(
    "Posez vos questions sur le règlement, les stages, le calendrier ou les démarches. "
    "Les réponses s'appuient uniquement sur les documents officiels de l'établissement."
)

with st.sidebar:
    st.markdown("### À propos")
    st.write("Chaque réponse cite les documents utilisés : cliquez sur **Sources** pour les consulter.")
    st.info("En cas de doute, la vie scolaire et le secrétariat restent vos interlocuteurs officiels.")
new_conversation_button("student_messages")

render_chat(
    client,
    "student_messages",
    placeholder="Une question sur les stages, le règlement, les dates ?",
    examples=[
        "Comment justifier une absence ?",
        "Quelles sont les dates des stages ?",
        "Le portable est-il autorisé ?",
    ],
)
