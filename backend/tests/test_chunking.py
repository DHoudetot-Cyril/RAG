import pytest

from app.chunking import chunk_sections, split_text
from app.parsers import Section

PARAGRAPH = (
    "Les élèves doivent justifier toute absence auprès de la vie scolaire dans un délai de 48 heures. "
    "Au-delà de trois absences injustifiées, la famille est convoquée par le conseiller principal d'éducation. "
)


def test_short_text_gives_single_chunk():
    assert split_text("Bonjour à tous.", chunk_size=100, chunk_overlap=10) == ["Bonjour à tous."]


def test_empty_text_gives_no_chunk():
    assert split_text("   \n  ", chunk_size=100, chunk_overlap=10) == []


def test_chunks_respect_max_size():
    text = "\n\n".join([PARAGRAPH * 3] * 10)
    chunks = split_text(text, chunk_size=400, chunk_overlap=80)
    assert len(chunks) > 1
    assert all(0 < len(c) <= 400 for c in chunks)


def test_consecutive_chunks_overlap():
    sentences = " ".join(f"Phrase numéro {i} du règlement." for i in range(60))
    chunks = split_text(sentences, chunk_size=200, chunk_overlap=60)
    for previous, current in zip(chunks, chunks[1:], strict=False):
        last_sentence = previous.rsplit(". ", 1)[-1]
        assert last_sentence.rstrip(".") in current


def test_no_content_is_lost():
    words = [f"mot{i}" for i in range(500)]
    chunks = split_text(" ".join(words), chunk_size=120, chunk_overlap=20)
    joined = " ".join(chunks)
    assert all(w in joined for w in words)


def test_very_long_word_is_hard_split():
    chunks = split_text("x" * 1000, chunk_size=300, chunk_overlap=0)
    assert [len(c) for c in chunks] == [300, 300, 300, 100]


def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        split_text("abc", chunk_size=100, chunk_overlap=100)


def test_chunk_sections_keeps_page_and_global_index():
    sections = [Section(PARAGRAPH * 4, page=1), Section(PARAGRAPH * 4, page=2)]
    chunks = chunk_sections(sections, chunk_size=250, chunk_overlap=40)
    assert {c.page for c in chunks} == {1, 2}
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_tiny_chunks_are_dropped():
    assert chunk_sections([Section("ok", page=1)], min_chars=30) == []
