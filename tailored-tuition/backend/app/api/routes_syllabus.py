"""Syllabus concepts and document uploads."""

from fastapi import APIRouter, HTTPException, UploadFile
from sqlalchemy import select

from app.api.deps import DB, KG, SettingsDep, concept_out
from app.api.schemas import ConceptOut, SyllabusDocumentOut
from app.domain.ingest import document_stats, ingest
from app.domain.rag_pipeline import retriever
from app.domain.syllabus_parser import SUPPORTED_SUFFIXES, UnsupportedFileError
from app.models import SyllabusDocument
from app.security.auth import GuardianDep, PrincipalDep, is_admin

router = APIRouter(prefix="/api/syllabus", tags=["syllabus"])


@router.get("/concepts", response_model=list[ConceptOut])
def list_concepts(kg: KG):
    return [concept_out(c) for c in kg.all()]


@router.get("/documents", response_model=list[SyllabusDocumentOut])
def list_documents(_: PrincipalDep, db: DB):
    docs = db.scalars(select(SyllabusDocument).order_by(SyllabusDocument.uploaded_at.desc()))
    return [document_stats(db, d) for d in docs]


@router.post("/upload", response_model=SyllabusDocumentOut, status_code=201)
async def upload(file: UploadFile, guardian: GuardianDep, db: DB, kg: KG, settings: SettingsDep):
    # Uploaded text is shown to every student's tutor, so only admins may add it.
    if not is_admin(guardian, settings):
        raise HTTPException(403, "Only administrators can upload syllabus files.")
    name = file.filename or "upload"
    if not name.lower().endswith(SUPPORTED_SUFFIXES):
        raise HTTPException(415, f"Unsupported file type. Use one of: {', '.join(SUPPORTED_SUFFIXES)}")
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB.")
    try:
        doc = ingest(db, kg, retriever, name, data)
    except UnsupportedFileError as exc:
        raise HTTPException(422, str(exc)) from exc
    return document_stats(db, doc)
