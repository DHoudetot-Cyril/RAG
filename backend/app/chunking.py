"""Découpage récursif du texte en morceaux (chunks) avec chevauchement.

On coupe d'abord sur les paragraphes, puis les lignes, puis les phrases, puis les mots,
pour ne jamais trancher une idée au milieu tant que c'est évitable. Le chevauchement
garantit qu'une information à cheval entre deux chunks reste retrouvable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .parsers import Section

_SENTENCE_END = re.compile(r"(?<=[.!?;:])\s+")


@dataclass(frozen=True)
class Chunk:
    text: str
    page: int | None
    index: int


def _split_units(text: str, max_size: int) -> list[str]:
    """Découpe `text` en unités dont aucune ne dépasse `max_size` caractères."""
    if len(text) <= max_size:
        return [text]
    for splitter in (lambda t: t.split("\n\n"), lambda t: t.split("\n"), _SENTENCE_END.split, str.split):
        parts = [p.strip() for p in splitter(text) if p.strip()]
        if len(parts) > 1:
            units: list[str] = []
            for part in parts:
                units.extend(_split_units(part, max_size))
            return units
    # Un seul "mot" plus long que max_size : coupe brute.
    return [text[i : i + max_size] for i in range(0, len(text), max_size)]


def split_text(text: str, chunk_size: int = 1200, chunk_overlap: int = 200) -> list[str]:
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap doit être strictement inférieur à chunk_size")
    text = text.strip()
    if not text:
        return []

    units = _split_units(text, chunk_size)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for unit in units:
        added = len(unit) + (1 if current else 0)
        if current and current_len + added > chunk_size:
            chunks.append(" ".join(current))
            # Conserve la fin du chunk précédent comme chevauchement.
            overlap: list[str] = []
            overlap_len = 0
            for previous in reversed(current):
                if overlap_len + len(previous) + 1 > chunk_overlap:
                    break
                overlap.insert(0, previous)
                overlap_len += len(previous) + 1
            current, current_len = overlap, max(overlap_len - 1, 0)
            # Si le chevauchement + l'unité dépasse encore, on abandonne le chevauchement.
            if current and current_len + len(unit) + 1 > chunk_size:
                current, current_len = [], 0
            added = len(unit) + (1 if current else 0)
        current.append(unit)
        current_len += added

    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_sections(
    sections: list[Section], chunk_size: int = 1200, chunk_overlap: int = 200, min_chars: int = 30
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section in sections:
        for piece in split_text(section.text, chunk_size, chunk_overlap):
            if len(piece) >= min_chars:
                chunks.append(Chunk(text=piece, page=section.page, index=len(chunks)))
    return chunks
