"""数字人形象管理路由。

管理形象配置（名称、图片、音色），激活后同步到 brain 层实时生效。
"""
import json
import os
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import AvatarConfig

router = APIRouter(prefix="/api/avatar", tags=["avatar"])

# 可用的 edge-tts 中文音色
AVAILABLE_VOICES = [
    {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓（女·活泼）", "gender": "女"},
    {"id": "zh-CN-YunxiNeural", "name": "云希（男·播音）", "gender": "男"},
    {"id": "zh-CN-YunjianNeural", "name": "云健（男·稳重）", "gender": "男"},
    {"id": "zh-CN-XiaoyiNeural", "name": "晓伊（女·年轻）", "gender": "女"},
    {"id": "zh-CN-YunyangNeural", "name": "云扬（男·新闻）", "gender": "男"},
    {"id": "zh-CN-XiaochenNeural", "name": "晓辰（女·温柔）", "gender": "女"},
    {"id": "zh-CN-XiaohanNeural", "name": "晓涵（女·知性）", "gender": "女"},
    {"id": "zh-CN-XiaomengNeural", "name": "晓梦（女·可爱）", "gender": "女"},
]


def _avatar_dir() -> Path:
    d = Path(os.getenv("AVATAR_DIR", "data/avatars"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sync_to_brain(voice: str, name: str):
    """同步音色配置到 brain 层（同一进程，直接调用）。"""
    try:
        from brain.adapter.livetalking_bridge import update_voice
        update_voice(voice, name)
        return True
    except Exception:
        return False


@router.get("/voices")
def list_voices():
    """获取所有可用的音色选项。"""
    return {"voices": AVAILABLE_VOICES}


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


@router.get("/active")
def get_active():
    """获取当前激活的形象配置。"""
    config_path = (
        Path(__file__).parent.parent.parent.parent
        / "brain" / "config" / "active_avatar.json"
    )
    try:
        if config_path.exists():
            return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"name": "小灵", "voice": "zh-CN-XiaoxiaoNeural", "avatar_id": "wav2lip256_avatar1"}


@router.post("/activate-voice")
def activate_voice(voice: str = Query(...), db: Session = Depends(get_db)):
    """直接激活一个音色（无需创建形象）。"""
    if not any(v["id"] == voice for v in AVAILABLE_VOICES):
        return {"error": f"不支持的音色: {voice}"}

    voice_name = next(v["name"] for v in AVAILABLE_VOICES if v["id"] == voice)
    _sync_to_brain(voice, voice_name)

    return {"voice": voice, "name": voice_name, "synced": True}


@router.post("/{aid}/activate")
def activate(aid: int, db: Session = Depends(get_db)):
    db.query(AvatarConfig).update({AvatarConfig.is_active: 0})
    av = db.query(AvatarConfig).get(aid)
    if not av:
        return {"error": "形象不存在"}
    av.is_active = 1
    db.commit()

    # 同步到 brain 层
    _sync_to_brain(av.voice, av.name)

    return {
        "active_id": aid,
        "name": av.name,
        "voice": av.voice,
        "synced": True,
    }
