import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import AvatarConfig

router = APIRouter(prefix="/api/avatar", tags=["avatar"])


def _avatar_dir() -> Path:
    d = Path(os.getenv("AVATAR_DIR", "data/avatars"))
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("")
def create(
    file: UploadFile = File(...),
    name: str = Form(...),
    voice: str = Form("zh-CN-XiaoxiaoNeural"),
    db: Session = Depends(get_db),
):
    dest = _avatar_dir() / file.filename
    dest.write_bytes(file.file.read())
    av = AvatarConfig(name=name, image_path=str(dest), voice=voice)
    db.add(av)
    db.commit()
    db.refresh(av)
    return {"id": av.id, "name": av.name, "image_path": av.image_path, "voice": av.voice}


@router.get("/list")
def list_all(db: Session = Depends(get_db)):
    return db.query(AvatarConfig).all()


@router.post("/{aid}/activate")
def activate(aid: int, db: Session = Depends(get_db)):
    db.query(AvatarConfig).update({AvatarConfig.is_active: 0})
    av = db.query(AvatarConfig).get(aid)
    av.is_active = 1
    db.commit()
    return {"active_id": aid}
