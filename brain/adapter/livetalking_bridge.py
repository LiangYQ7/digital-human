"""LiveTalking 数字人桥接适配器。

通过 HTTP 将回复文本推给 LiveTalking 服务，支持动态音色切换。
CosyVoice 路径：直接调 DashScope 云端 TTS（~2s），不再经过本地 CosyVoice 服务器中转。
"""
import base64
import json
import os
import threading
from pathlib import Path

import requests

_ACTIVE_CONFIG: dict | None = None
_CLOUD_VOICE_ID: str | None = None
_CLOUD_LOCK = threading.Lock()


def _get_active_voice() -> str:
    """读取当前激活的音色配置。"""
    global _ACTIVE_CONFIG
    config_path = Path(__file__).parent.parent / "config" / "active_avatar.json"
    try:
        if config_path.exists():
            _ACTIVE_CONFIG = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    if _ACTIVE_CONFIG:
        return _ACTIVE_CONFIG.get("voice", "zh-CN-XiaoxiaoNeural")
    return "zh-CN-XiaoxiaoNeural"


def _base_url() -> str:
    return f"http://127.0.0.1:{os.getenv('LIVETALKING_PORT', '8010')}"


def _dashscope_key() -> str:
    return os.getenv("DASHSCOPE_API_KEY", "")


def _clone_dir(voice: str) -> Path:
    return Path(__file__).parent.parent.parent / "admin" / "backend" / "_clones" / voice


# ── 云端 TTS（DashScope cosyvoice-v3.5-flash，~1-2s）───────────────

def _ensure_cloud_voice(voice: str) -> str | None:
    """注册克隆音色到 DashScope，返回 voice_id。模块级缓存，只注册一次。"""
    global _CLOUD_VOICE_ID
    if _CLOUD_VOICE_ID:
        return _CLOUD_VOICE_ID

    with _CLOUD_LOCK:
        if _CLOUD_VOICE_ID:
            return _CLOUD_VOICE_ID
        api_key = _dashscope_key()
        if not api_key:
            return None
        cd = _clone_dir(voice)
        if not (cd / "ref.wav").exists():
            return None

        ref_b64 = base64.b64encode((cd / "ref.wav").read_bytes()).decode()
        ref_txt = ""
        if (cd / "ref_text.txt").exists():
            ref_txt = (cd / "ref_text.txt").read_text(encoding="utf-8").strip()

        payload = {
            "model": "voice-enrollment",
            "input": {
                "action": "create_voice",
                "target_model": "cosyvoice-v3.5-flash",
                "prefix": voice[:10],
                "url": f"data:audio/wav;base64,{ref_b64}",
            },
        }
        if ref_txt:
            payload["input"]["reference_text"] = ref_txt

        try:
            r = requests.post(
                "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload, timeout=30,
            )
            if r.status_code == 200:
                vid = r.json().get("output", {}).get("voice_id")
                if vid:
                    _CLOUD_VOICE_ID = vid
                    print(f"[BRIDGE] 云端音色 {voice} → {vid}", flush=True)
                    return vid
            print(f"[BRIDGE] 注册音色 {voice}: {r.status_code} {r.text[:200]}", flush=True)
        except Exception as e:
            print(f"[BRIDGE] 注册音色异常: {e}", flush=True)
        return None


def _cloud_tts(text: str, voice: str) -> bytes | None:
    """直接调 DashScope 云端 TTS，返回 WAV 音频数据。"""
    api_key = _dashscope_key()
    if not api_key:
        return None

    voice_id = _ensure_cloud_voice(voice)
    if not voice_id:
        return None

    payload = {
        "model": "cosyvoice-v3.5-flash",
        "input": {
            "text": text,
            "voice": voice_id,
            "format": "wav",
            "sample_rate": 24000,
        },
    }
    try:
        r = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload, timeout=30,
        )
        if r.status_code != 200:
            print(f"[BRIDGE] 云端TTS失败: {r.status_code} {r.text[:200]}", flush=True)
            return None
        data = r.json()
        audio_url = data.get("output", {}).get("audio", {}).get("url", "")
        if not audio_url:
            print(f"[BRIDGE] 云端TTS无音频: {r.text[:200]}", flush=True)
            return None
        r2 = requests.get(audio_url, timeout=15)
        if r2.status_code == 200:
            print(f"[BRIDGE] 云端TTS完成: {len(r2.content)} bytes", flush=True)
            return r2.content
    except Exception as e:
        print(f"[BRIDGE] 云端TTS异常: {e}", flush=True)
    return None


# ── 主入口 ─────────────────────────────────────────────────────

def send_text(text: str, sessionid: str) -> bool:
    """把回复文本推给数字人。cosyvoice 走 DashScope 云端 TTS，edge-tts 走 LiveTalking。"""
    voice = _get_active_voice()

    # CosyVoice 路径 → DashScope 云端 TTS（快）
    if voice.startswith('cosyvoice:'):
        clone_name = voice.replace('cosyvoice:', '')
        # 1) 云端 TTS
        audio = _cloud_tts(text, clone_name)
        if audio is None:
            # 2) 回退到本地 CosyVoice 服务器
            print(f"[BRIDGE] 云端TTS未成功，回退本地 CosyVoice...", flush=True)
            try:
                r = requests.post('http://127.0.0.1:8091/v1/audio/speech',
                                  json={'input': text, 'voice': clone_name}, timeout=120)
                if r.status_code != 200:
                    print(f"[BRIDGE] 本地TTS失败: {r.status_code}", flush=True)
                    return False
                audio = r.content
            except Exception as e:
                print(f"[BRIDGE] 本地TTS异常: {e}", flush=True)
                return False
        # 3) 推给 LiveTalking
        try:
            files = {'file': ('tts.wav', audio, 'audio/wav')}
            r = requests.post(f"{_base_url()}/humanaudio",
                              data={'sessionid': sessionid}, files=files, timeout=15)
            ok = r.status_code == 200
            if ok:
                print(f"[BRIDGE] /humanaudio OK", flush=True)
            else:
                print(f"[BRIDGE] /humanaudio 失败: {r.status_code}", flush=True)
            return ok
        except Exception as e:
            print(f"[BRIDGE] /humanaudio 异常: {e}", flush=True)
            return False

    # edge-tts 路径
    try:
        r = requests.post(f"{_base_url()}/human",
            json={'text': text, 'type': 'echo', 'sessionid': sessionid,
                  'tts': {'ref_file': voice}},
            timeout=10)
        ok = r.status_code == 200 and r.json().get("code", -1) == 0
        if not ok:
            print(f"[SEND] /human 失败: {r.status_code} {r.text[:200]}", flush=True)
        return ok
    except Exception as e:
        print(f"[SEND] 异常: {e}", flush=True)
        return False


def get_active_config() -> dict:
    """获取当前激活的形象配置。"""
    _get_active_voice()  # 刷新缓存
    return _ACTIVE_CONFIG or {
        "name": "小灵",
        "avatar_id": "wav2lip256_avatar1",
        "voice": "zh-CN-XiaoxiaoNeural",
    }


def update_voice(voice: str, name: str = ""):
    """更新音色配置（由管理后台调用）。"""
    global _CLOUD_VOICE_ID
    config_path = Path(__file__).parent.parent / "config" / "active_avatar.json"
    config = {
        "name": name or "小灵",
        "avatar_id": "wav2lip256_avatar1",
        "voice": voice,
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    global _ACTIVE_CONFIG
    _ACTIVE_CONFIG = config
    _CLOUD_VOICE_ID = None  # 切换音色后重新注册

    # 同步到 LiveTalking 的 config.yaml
    try:
        lt_config = Path(__file__).parent.parent.parent / "third_party" / "LiveTalking" / "config.yaml"
        if lt_config.exists():
            content = lt_config.read_text(encoding="utf-8")
            import re
            content = re.sub(r'REF_FILE:\s*.*', f'REF_FILE: {voice}', content)
            lt_config.write_text(content, encoding="utf-8")
    except Exception:
        pass
