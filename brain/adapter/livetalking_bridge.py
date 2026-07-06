import os

import requests


def _base_url() -> str:
    return f"http://127.0.0.1:{os.getenv('LIVETALKING_PORT', '8010')}"


def send_text(text: str) -> bool:
    """把回复文本推给 LiveTalking，由其合成语音并驱动口型。"""
    try:
        r = requests.post(
            f"{_base_url()}/human",
            json={"text": text},
            timeout=5,
        )
        return r.status_code == 200 and r.json().get("code", -1) == 0
    except Exception:
        return False
