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
    """列出所有可用音色（edge-tts + CosyVoice 克隆音色）。"""
    voices = list(AVAILABLE_VOICES)
    try:
        import requests as req
        r = req.get("http://127.0.0.1:8091/v1/audio/voices", timeout=3)
        if r.ok:
            data = r.json()
            for v in data.get("uploaded_voices", []):
                voices.append({"id": f"cosyvoice:{v['name']}", "name": f"{v['name']}（CosyVoice）", "gender": "克隆"})
    except Exception:
        pass
    return {"voices": voices}


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
        Path(__file__).parent.parent.parent.parent.parent
        / "brain" / "config" / "active_avatar.json"
    )
    try:
        if config_path.exists():
            return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"name": "小灵", "voice": "zh-CN-XiaoxiaoNeural", "avatar_id": "wav2lip256_avatar1"}


@router.get("/disk-avatars")
def list_disk_avatars():
    """扫描磁盘 third_party/LiveTalking/data/avatars/ 下的可用形象目录。"""
    base = (
        Path(__file__).parent.parent.parent.parent.parent
        / "third_party" / "LiveTalking" / "data" / "avatars"
    )
    if not base.exists():
        return {"avatars": []}
    avatars = []
    for d in sorted(base.iterdir()):
        if d.is_dir():
            # 检查是否包含完整的形象数据
            has_coords = (d / "coords.pkl").exists()
            has_full = (d / "full_imgs").is_dir()
            has_face = (d / "face_imgs").is_dir()
            avatars.append({
                "id": d.name,
                "valid": has_coords and has_full and has_face,
            })
    return {"avatars": avatars}


@router.post("/switch-avatar")
def switch_avatar(avatar_id: str = Query(...)):
    """切换当前激活形象的 avatar_id。自动清空 LiveTalking 旧会话。"""
    config_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "brain" / "config" / "active_avatar.json"
    )
    try:
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
        else:
            config = {"voice": "zh-CN-XiaoxiaoNeural"}
        config["avatar_id"] = avatar_id
        config["name"] = avatar_id
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 清空 LiveTalking 所有旧会话，避免槽位占满导致用户端连不上
        try:
            import requests as _r
            _r.post("http://127.0.0.1:8010/api/admin/reset-sessions", timeout=5)
        except Exception:
            pass

        return {"avatar_id": avatar_id, "synced": True}
    except Exception as e:
        return {"error": str(e), "synced": False}


@router.post("/delete-avatar")
def delete_avatar(avatar_id: str = Query(...)):
    """删除磁盘上的形象目录（内置形象 wav2lip256_avatar1 受保护）。"""
    PROTECTED = ["wav2lip256_avatar1"]
    if avatar_id in PROTECTED:
        return {"error": f"内置形象 {avatar_id} 不允许删除", "synced": False}

    base = (
        Path(__file__).parent.parent.parent.parent.parent
        / "third_party" / "LiveTalking" / "data" / "avatars"
    )
    target = base / avatar_id
    if not target.exists() or not target.is_dir():
        return {"error": f"形象目录不存在: {avatar_id}", "synced": False}

    import shutil
    shutil.rmtree(target)
    return {"avatar_id": avatar_id, "deleted": True}


@router.post("/activate-voice")
def activate_voice(voice: str = Query(...)):
    """直接激活一个音色（支持 edge-tts 和 CosyVoice 克隆音色）。"""
    edge_v = next((v for v in AVAILABLE_VOICES if v["id"] == voice), None)
    if edge_v:
        _sync_to_brain(voice, edge_v["name"])
        return {"voice": voice, "name": edge_v["name"], "synced": True}
    if voice.startswith("cosyvoice:"):
        clone_name = voice.replace("cosyvoice:", "")
        _sync_to_brain(voice, clone_name)
        return {"voice": voice, "name": clone_name, "synced": True}
    return {"error": f"不支持的音色: {voice}", "synced": False}


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
