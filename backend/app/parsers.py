"""Extraction de texte multi-formats : PDF, DOCX, PPTX, TXT, Markdown.

Chaque parseur renvoie une liste de `Section` (texte + numéro de page/diapositive quand
il existe), ce qui permet ensuite de citer précisément la page source dans les réponses.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Section:
    text: str
    page: int | None = None


class UnsupportedFormatError(ValueError):
    pass


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}

_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_SPACES = re.compile(r"[ \t ]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Normalise les espaces et recolle les mots coupés en fin de ligne."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MANY_NEWLINES.sub("\n\n", text)
    return text.strip()


def _parse_pdf(data: bytes) -> list[Section]:
    import pymupdf

    sections = []
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for page_number, page in enumerate(doc, start=1):
            text = clean_text(page.get_text("text"))
            if text:
                sections.append(Section(text=text, page=page_number))
    return sections


def _parse_docx(data: bytes) -> list[Section]:
    import docx

    document = docx.Document(io.BytesIO(data))
    blocks: list[str] = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                blocks.append(" | ".join(dict.fromkeys(cells)))
    text = clean_text("\n\n".join(blocks))
    return [Section(text=text)] if text else []


def _parse_pptx(data: bytes) -> list[Section]:
    from pptx import Presentation

    presentation = Presentation(io.BytesIO(data))
    sections = []
    for slide_number, slide in enumerate(presentation.slides, start=1):
        parts = []
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text.strip():
                parts.append(shape.text_frame.text)
            elif getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if cells:
                        parts.append(" | ".join(cells))
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            parts.append(slide.notes_slide.notes_text_frame.text)
        text = clean_text("\n\n".join(parts))
        if text:
            sections.append(Section(text=text, page=slide_number))
    return sections


def _parse_text(data: bytes) -> list[Section]:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    text = clean_text(text)
    return [Section(text=text)] if text else []


_PARSERS = {
    ".pdf": _parse_pdf,
    ".docx": _parse_docx,
    ".pptx": _parse_pptx,
    ".txt": _parse_text,
    ".md": _parse_text,
}


def extract_sections(filename: str, data: bytes) -> list[Section]:
    extension = Path(filename).suffix.lower()
    parser = _PARSERS.get(extension)
    if parser is None:
        raise UnsupportedFormatError(
            f"Format '{extension or 'inconnu'}' non supporté. Formats acceptés : "
            + ", ".join(sorted(SUPPORTED_EXTENSIONS))
        )
    return parser(data)
