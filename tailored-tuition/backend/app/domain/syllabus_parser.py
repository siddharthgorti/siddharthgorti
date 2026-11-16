"""Turn an uploaded syllabus file (PDF / TXT / MD) into titled, sized chunks.

Known limitation: PDF text extraction loses mathematical layout (fractions,
superscripts, matrices). Retrieval still works on the surrounding prose, but
for high-fidelity maths a LaTeX/OCR pipeline (e.g. Nougat, Mathpix) is needed.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

from pypdf import PdfReader

SUPPORTED_SUFFIXES = (".pdf", ".txt", ".md")

# "1.2 Sets and their Representations", "Chapter 3", "EXERCISE 1.1", "## Heading"
_HEADING = re.compile(
    r"^(?:#{1,4}\s+.+|(?:chapter|unit)\s+\d+.*|exercise\s+\d+(?:\.\d+)?|\d{1,2}(?:\.\d{1,2}){0,2}\s+[A-Z][^.!?]{2,80})$",
    re.IGNORECASE,
)

CHUNK_CHARS = 1200
OVERLAP_CHARS = 200


@dataclass
class ParsedChunk:
    section: str
    text: str


class UnsupportedFileError(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:  # pypdf raises a variety of errors on bad files
            raise UnsupportedFileError(f"Could not read PDF: {exc}") from exc
        text = "\n".join(pages)
        if not text.strip():
            raise UnsupportedFileError("This PDF has no extractable text (it may be a scanned image).")
        return text
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="replace")
    raise UnsupportedFileError(f"Unsupported file type. Use one of: {', '.join(SUPPORTED_SUFFIXES)}")


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split text into (heading, body) pairs using heading heuristics."""
    sections: list[tuple[str, list[str]]] = [("Introduction", [])]
    for raw in text.splitlines():
        line = raw.strip()
        if line and len(line) <= 90 and _HEADING.match(line):
            sections.append((line.lstrip("#").strip(), []))
        else:
            sections[-1][1].append(raw)
    out = []
    for heading, lines in sections:
        body = _normalise("\n".join(lines))
        if body:
            out.append((heading, body))
    return out


def chunk_text(body: str, size: int = CHUNK_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    """Greedy paragraph packing into ~size-char windows with overlap."""
    if len(body) <= size:
        return [body]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        while len(para) > size:  # a single huge paragraph: hard-split it
            if current:
                chunks.append(current)
                current = ""
            chunks.append(para[:size])
            para = para[size - overlap :]
        if current and len(current) + len(para) + 2 > size:
            chunks.append(current)
            current = current[-overlap:] + "\n\n" + para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks


def parse_document(filename: str, data: bytes) -> list[ParsedChunk]:
    text = extract_text(filename, data)
    return [
        ParsedChunk(section=heading[:255], text=c) for heading, body in split_sections(text) for c in chunk_text(body)
    ]


def _normalise(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
