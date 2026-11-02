import io

import pytest

from app.parsers import UnsupportedFormatError, clean_text, extract_sections


def test_clean_text_fixes_hyphenation_and_spaces():
    assert clean_text("inter-\nne   au lycée\n\n\n\nfin") == "interne au lycée\n\nfin"


def test_txt_and_markdown():
    assert extract_sections("notes.txt", b"Bonjour\nle monde")[0].text == "Bonjour\nle monde"
    sections = extract_sections("README.MD", b"# Titre\n\nContenu")
    assert sections[0].text == "# Titre\n\nContenu"
    assert sections[0].page is None


def test_txt_latin1_fallback():
    assert extract_sections("vieux.txt", "élève".encode("cp1252"))[0].text == "élève"


def test_pdf_pages_are_numbered():
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    for text in ("Page un : horaires", "Page deux : cantine"):
        page = doc.new_page()
        page.insert_text((72, 72), text)
    data = doc.tobytes()
    sections = extract_sections("reglement.pdf", data)
    assert [s.page for s in sections] == [1, 2]
    assert "cantine" in sections[1].text


def test_docx_paragraphs_and_tables():
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_paragraph("Calendrier des stages")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Début"
    table.rows[0].cells[1].text = "3 mars"
    buffer = io.BytesIO()
    document.save(buffer)
    text = extract_sections("stages.docx", buffer.getvalue())[0].text
    assert "Calendrier des stages" in text
    assert "Début | 3 mars" in text


def test_pptx_slides_are_numbered():
    pptx = pytest.importorskip("pptx")
    from pptx.util import Inches

    presentation = pptx.Presentation()
    for title in ("Bienvenue", "Les examens"):
        slide = presentation.slides.add_slide(presentation.slide_layouts[5])
        slide.shapes.title.text = title
        slide.shapes.add_textbox(Inches(1), Inches(2), Inches(4), Inches(1)).text_frame.text = f"Détails {title}"
    buffer = io.BytesIO()
    presentation.save(buffer)
    sections = extract_sections("presentation.pptx", buffer.getvalue())
    assert [s.page for s in sections] == [1, 2]
    assert "Les examens" in sections[1].text


def test_unsupported_format():
    with pytest.raises(UnsupportedFormatError):
        extract_sections("image.png", b"\x89PNG")
