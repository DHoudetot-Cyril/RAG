# syntax=docker/dockerfile:1.6
# Image unique pour les trois interfaces : le service docker compose choisit le script à lancer.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_CLIENT_TOOLBAR_MODE=minimal

WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
COPY *.py ./

RUN useradd --create-home --uid 1000 rag
USER rag

ENV APP=student.py
EXPOSE 8501
CMD ["sh", "-c", "streamlit run \"$APP\" --server.port=8501 --server.address=0.0.0.0"]
