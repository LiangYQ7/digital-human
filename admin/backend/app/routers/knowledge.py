import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import KnowledgeDoc

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _upload_dir() -> Path:
    d = Path(os.getenv("KB_UPLOAD_DIR", "data/kb"))
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("/upload")
def upload(
    file: UploadFile = File(...),
    title: str = Form(...),
    db: Session = Depends(get_db),
):
    dest = _upload_dir() / file.filename
    dest.write_bytes(file.file.read())
    doc = KnowledgeDoc(title=title, source_path=str(dest), status="pending")
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {
        "id": doc.id,
        "title": doc.title,
        "source_path": doc.source_path,
        "status": doc.status,
    }


@router.get("/docs")
def list_docs(db: Session = Depends(get_db)):
    return db.query(KnowledgeDoc).order_by(KnowledgeDoc.id.desc()).all()


@router.post("/reindex")
def reindex(db: Session = Depends(get_db)):
    """触发 brain 的 ingest（子进程调用）"""
    folder = _upload_dir()
    subprocess.Popen([
        sys.executable,
        "-c",
        f"from pathlib import Path; from brain.rag.retriever import ingest_folder; ingest_folder(Path('{folder}'))",
    ])
    docs = db.query(KnowledgeDoc).filter(KnowledgeDoc.status == "pending").all()
    for d in docs:
        d.status = "ingested"
    db.commit()
    return {"reindexed": len(docs)}
