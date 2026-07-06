import time

from brain.adapter.livetalking_bridge import send_text
from brain.llm_client import chat


def handle_user_input(text: str, image_path: str | None = None) -> dict:
    """完整链路：ASR 文本 → LLM → LiveTalking。

    Args:
        text: 用户输入文本
        image_path: 可选图片路径

    Returns:
        {
            "reply": LLM 回复文本,
            "delivered": 是否成功推给 LiveTalking,
            "latency_sec": 端到端延迟（秒）,
        }
    """
    t0 = time.time()
    reply = chat(text, image_path=image_path)
    delivered = send_text(reply)
    return {
        "reply": reply,
        "delivered": delivered,
        "latency_sec": round(time.time() - t0, 2),
    }
