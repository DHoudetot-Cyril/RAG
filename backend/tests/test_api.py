import json

from app.rag import NO_ANSWER
from tests.conftest import auth

PUBLIC_DOC = (
    "Règlement intérieur du lycée. Les absences doivent être justifiées auprès de la vie scolaire "
    "dans un délai de quarante-huit heures. La cantine ouvre à onze heures trente."
)
SECRET_DOC = (
    "Document confidentiel de la direction. Le budget prévisionnel du conseil d'administration "
    "prévoit une enveloppe de rénovation des locaux pour l'année prochaine."
)


def upload(client, name: str, content: str, level: str, role: str = "admin"):
    return client.post(
        "/documents",
        headers=auth(role),
        data={"level": level},
        files={"file": (name, content.encode(), "text/plain")},
    )


def seed(client):
    assert upload(client, "reglement.txt", PUBLIC_DOC, "level1").status_code == 201
    assert upload(client, "budget.txt", SECRET_DOC, "level2").status_code == 201


# ------------------------------------------------------------------ système
def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["qdrant"] is True


def test_authentication_required(client):
    assert client.post("/chat", json={"question": "Bonjour"}).status_code == 401
    assert client.get("/me", headers={"X-API-Key": "faux"}).status_code == 401


def test_whoami(client):
    assert client.get("/me", headers=auth("student")).json() == {"role": "student", "levels": ["level1"]}
    assert client.get("/me", headers=auth("direction")).json()["levels"] == ["level1", "level2"]


# ---------------------------------------------------------------- ingestion
def test_ingestion_is_idempotent_and_versioned(client):
    first = upload(client, "reglement.txt", PUBLIC_DOC, "level1").json()
    assert first["status"] == "ingested"
    assert first["chunks"] >= 1

    again = upload(client, "reglement.txt", PUBLIC_DOC, "level1").json()
    assert again["status"] == "unchanged"
    assert again["chunks"] == first["chunks"]

    updated = upload(client, "reglement.txt", PUBLIC_DOC + " Nouvelle règle sur les portables.", "level1").json()
    assert updated["status"] == "updated"

    documents = client.get("/documents", headers=auth("admin")).json()
    assert len(documents) == 1, "une nouvelle version ne doit pas créer de doublon"


def test_only_admin_can_ingest(client):
    assert upload(client, "x.txt", PUBLIC_DOC, "level1", role="student").status_code == 403
    assert upload(client, "x.txt", PUBLIC_DOC, "level1", role="direction").status_code == 403


def test_unsupported_and_empty_files(client):
    assert upload(client, "photo.png", "binaire", "level1").status_code == 415
    assert upload(client, "vide.txt", "   ", "level1").status_code == 422


def test_file_too_large(client):
    assert upload(client, "gros.txt", "a" * (1024 * 1024 + 10), "level1").status_code == 413


def test_path_in_filename_is_neutralised(client):
    body = upload(client, "../../etc/reglement.txt", PUBLIC_DOC, "level1").json()
    assert body["document"] == "reglement.txt"


# ---------------------------------------------------------------- documents
def test_documents_visibility_by_role(client):
    seed(client)
    student = {d["document"] for d in client.get("/documents", headers=auth("student")).json()}
    direction = {d["document"] for d in client.get("/documents", headers=auth("direction")).json()}
    assert student == {"reglement.txt"}
    assert direction == {"reglement.txt", "budget.txt"}
    assert client.get("/documents?level=level2", headers=auth("student")).status_code == 403


def test_delete_document(client):
    seed(client)
    doc = next(d for d in client.get("/documents", headers=auth("admin")).json() if d["level"] == "level2")
    url = f"/documents/level2/{doc['document_id']}"
    assert client.delete(url, headers=auth("direction")).status_code == 403
    assert client.delete(url, headers=auth("admin")).status_code == 200
    assert client.delete(url, headers=auth("admin")).status_code == 404
    assert {d["document"] for d in client.get("/documents", headers=auth("admin")).json()} == {"reglement.txt"}


# --------------------------------------------------------------------- chat
def test_chat_returns_sourced_answer(client, fake_llm):
    seed(client)
    response = client.post("/chat", headers=auth("student"), json={"question": "Comment justifier les absences ?"})
    body = response.json()
    assert response.status_code == 200
    assert body["answer"].startswith("Réponse factice")
    assert body["sources"][0]["document"] == "reglement.txt"
    assert body["levels_searched"] == ["level1"]
    system_prompt = fake_llm.calls[-1][0]["content"]
    assert "[1] reglement.txt" in system_prompt


def test_student_never_sees_level2_content(client, fake_llm):
    seed(client)
    body = client.post(
        "/chat", headers=auth("student"), json={"question": "Quel est le budget de rénovation des locaux ?"}
    ).json()
    assert all(s["level"] == "level1" for s in body["sources"])
    assert all("budget" not in call[0]["content"] for call in fake_llm.calls)


def test_student_cannot_request_level2(client):
    response = client.post("/chat", headers=auth("student"), json={"question": "budget", "levels": ["level2"]})
    assert response.status_code == 403


def test_direction_searches_both_levels(client):
    seed(client)
    body = client.post(
        "/chat", headers=auth("direction"), json={"question": "Quel est le budget de rénovation des locaux ?"}
    ).json()
    assert body["sources"][0]["document"] == "budget.txt"
    assert body["sources"][0]["level"] == "level2"


def test_no_relevant_document_skips_llm(client, fake_llm):
    seed(client)
    body = client.post("/chat", headers=auth("student"), json={"question": "zzzz qwerty xylophone"}).json()
    assert body["answer"] == NO_ANSWER
    assert body["sources"] == []
    assert fake_llm.calls == []


def test_history_is_forwarded(client, fake_llm):
    seed(client)
    history = [
        {"role": "user", "content": "Parlons des absences."},
        {"role": "assistant", "content": "D'accord."},
    ]
    client.post(
        "/chat", headers=auth("student"), json={"question": "Quel délai pour les absences ?", "history": history}
    )
    messages = fake_llm.calls[-1]
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]


def test_chat_stream_ndjson(client):
    seed(client)
    with client.stream(
        "POST", "/chat/stream", headers=auth("student"), json={"question": "Quand ouvre la cantine ?"}
    ) as response:
        events = [json.loads(line) for line in response.iter_lines() if line]
    assert events[0]["type"] == "sources"
    assert events[0]["sources"][0]["document"] == "reglement.txt"
    assert "".join(e["content"] for e in events if e["type"] == "token") == "Réponse factice [1]."
    assert events[-1]["type"] == "done"


def test_search_without_generation(client, fake_llm):
    seed(client)
    sources = client.post("/search", headers=auth("direction"), json={"question": "budget rénovation"}).json()
    assert sources[0]["document"] == "budget.txt"
    assert fake_llm.calls == []
    assert (
        client.post("/search", headers=auth("student"), json={"question": "x", "levels": ["level2"]}).status_code == 403
    )
