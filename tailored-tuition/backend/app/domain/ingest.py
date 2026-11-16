"""Store a parsed syllabus document and its chunks, tagging each chunk with
its best-matching concept so retrieval can favour the current topic."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.knowledge_graph import KnowledgeGraph
from app.domain.rag_pipeline import Retriever
from app.domain.syllabus_parser import parse_document
from app.models import Chunk, SyllabusDocument


def ingest(db: Session, kg: KnowledgeGraph, retriever: Retriever, filename: str, data: bytes) -> SyllabusDocument:
    parsed = parse_document(filename, data)
    doc = SyllabusDocument(filename=Path(filename).name[:255])
    db.add(doc)
    for p in parsed:
        db.add(
            Chunk(document=doc, section=p.section, text=p.text, concept_id=kg.match_concept(f"{p.section} {p.text}"))
        )
    db.commit()
    retriever.invalidate()
    return doc


def document_stats(db: Session, doc: SyllabusDocument) -> dict:
    chunks, sections = db.execute(
        select(func.count(Chunk.id), func.count(func.distinct(Chunk.section))).where(Chunk.document_id == doc.id)
    ).one()
    return {
        "id": doc.id,
        "filename": doc.filename,
        "sections": sections,
        "chunks": chunks,
        "uploaded_at": doc.uploaded_at,
    }


def seed_samples(db: Session, kg: KnowledgeGraph, retriever: Retriever, folder: Path) -> int:
    """Ingest bundled sample notes once, on an empty database."""
    if db.scalar(select(func.count(SyllabusDocument.id))):
        return 0
    n = 0
    for path in sorted(folder.glob("*.md")) + sorted(folder.glob("*.txt")):
        ingest(db, kg, retriever, path.name, path.read_bytes())
        n += 1
    return n
