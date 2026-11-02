"""Composants Streamlit communs : en-tête, chat en streaming, affichage des sources."""

from __future__ import annotations

import os

import streamlit as st

from api_client import ApiClient, ApiError

LEVEL_LABELS = {"level1": "Niveau 1 · Public", "level2": "Niveau 2 · Direction"}

CSS = """
<style>
  .block-container { padding-top: 2rem; max-width: 1100px; }
  .source-card { border-left: 3px solid #4f8bf9; padding: .4rem .8rem; margin-bottom: .6rem;
                 background: rgba(79,139,249,.06); border-radius: 4px; font-size: .9rem; }
  .source-meta { color: #6b7280; font-size: .8rem; }
  .badge { display: inline-block; padding: 0 .45rem; border-radius: 999px; font-size: .72rem;
           background: #e5e7eb; color: #111827; margin-left: .3rem; }
  .badge.level2 { background: #fde2e2; color: #991b1b; }
</style>
"""


def setup_page(title: str, icon: str, role_env: str) -> ApiClient:
    st.set_page_config(page_title=f"RAG École · {title}", page_icon=icon, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    backend = os.getenv("BACKEND_URL", "http://localhost:8080")
    api_key = os.getenv(role_env, "")
    if not api_key:
        st.error(f"Variable d'environnement {role_env} manquante : l'interface ne peut pas s'authentifier.")
        st.stop()
    return ApiClient(backend, api_key)


def render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander(f"📎 Sources ({len(sources)})"):
        for number, src in enumerate(sources, start=1):
            page = f" · page {src['page']}" if src.get("page") else ""
            level_class = "level2" if src["level"] == "level2" else ""
            st.markdown(
                f"<div class='source-card'><b>[{number}] {src['document']}</b>{page}"
                f"<span class='badge {level_class}'>{LEVEL_LABELS.get(src['level'], src['level'])}</span>"
                f"<div class='source-meta'>pertinence {src['score']:.2f}</div>"
                f"<div>{_escape(src['excerpt'])}</div></div>",
                unsafe_allow_html=True,
            )


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")


def render_chat(
    client: ApiClient,
    state_key: str,
    *,
    levels: list[str] | None = None,
    placeholder: str = "Posez votre question…",
    examples: list[str] | None = None,
) -> None:
    messages: list[dict] = st.session_state.setdefault(state_key, [])

    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            render_sources(message.get("sources", []))

    question = st.chat_input(placeholder)
    if not messages and examples and not question:
        st.caption("Exemples de questions :")
        columns = st.columns(len(examples))
        for column, example in zip(columns, examples, strict=True):
            if column.button(example, use_container_width=True):
                question = example

    if not question:
        return

    history = [{"role": m["role"], "content": m["content"]} for m in messages]
    messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        state: dict = {"sources": [], "error": None}

        def tokens():
            try:
                for event in client.stream_chat(question, history, levels):
                    if event["type"] == "sources":
                        state["sources"] = event["sources"]
                    elif event["type"] == "token":
                        yield event["content"]
                    elif event["type"] == "error":
                        state["error"] = event["detail"]
            except ApiError as exc:
                state["error"] = str(exc)

        with st.spinner("Recherche dans les documents…"):
            answer = st.write_stream(tokens())
        if state["error"]:
            st.error(state["error"])
            messages.pop()  # on ne garde pas une question restée sans réponse
            return
        render_sources(state["sources"])

    messages.append({"role": "assistant", "content": answer or "", "sources": state["sources"]})


def new_conversation_button(state_key: str) -> None:
    if st.sidebar.button("🆕 Nouvelle conversation", use_container_width=True):
        st.session_state[state_key] = []
        st.rerun()


def health_sidebar(client: ApiClient) -> None:
    with st.sidebar:
        st.subheader("État du système")
        try:
            health = client.health()
        except ApiError as exc:
            st.error(f"API injoignable : {exc}")
            return
        st.write(("🟢" if health["qdrant"] else "🔴") + " Base vectorielle (Qdrant)")
        st.write(("🟢" if health["llm"] else "🔴") + " Modèle de langage")
        st.caption(f"LLM : {health['llm_model']}\n\nEmbeddings : {health['embedding_model']}")
