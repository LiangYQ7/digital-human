"""LiveTalking 数字人桥接适配器。

通过 HTTP 将回复文本推给 LiveTalking 服务，支持动态音色切换。
CosyVoice 路径 → 本地 CosyVoice 服务器(8091) → 云端 DashScope 合成（~2s）。
"""
import json
import os
from pathlib import Path

import requests

_ACTIVE_CONFIG: dict | None = None


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


# ── 主入口 ─────────────────────────────────────────────────────

def send_text(text: str, sessionid: str) -> bool:
    """把回复文本推给数字人。CosyVoice 走本地服务合成音频，edge-tts 走 LiveTalking。"""
    voice = _get_active_voice()

    # CosyVoice 音色：通过本地 CosyVoice 服务合成（内部走 DashScope 云端，~2-3s）
    if voice.startswith('cosyvoice:'):
        clone_name = voice.replace('cosyvoice:', '')
        try:
            r = requests.post('http://127.0.0.1:8091/v1/audio/speech',
                              json={'input': text, 'voice': clone_name}, timeout=60)
            if r.status_code != 200:
                print(f"[BRIDGE] TTS 失败 ({clone_name}): {r.status_code}", flush=True)
                return False
            print(f"[BRIDGE] TTS 完成 ({clone_name}): {len(r.content)} bytes", flush=True)
            files = {'file': ('tts.wav', r.content, 'audio/wav')}
            r2 = requests.post(f"{_base_url()}/humanaudio",
                               data={'sessionid': sessionid}, files=files, timeout=15)
            if r2.status_code != 200:
                print(f"[BRIDGE] /humanaudio 失败: {r2.status_code}", flush=True)
                return False
            print(f"[BRIDGE] /humanaudio OK", flush=True)
            return True
        except Exception as e:
            print(f"[BRIDGE] 异常: {e}", flush=True)
            return False

    # edge-tts 音色走 LiveTalking
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
