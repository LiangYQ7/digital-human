"""会话记忆模块。

每个 sessionid 保留最近 N 轮对话，支持多轮追问。
"""
import time
from collections import deque
from threading import Lock

# 每个会话最多保留的对话轮数
MAX_ROUNDS = 5
# 会话过期时间（秒）：30 分钟无活动自动清理
SESSION_TTL = 30 * 60

_store: dict[str, deque[tuple[str, str]]] = {}  # sessionid → [(role, text), ...]
_timestamps: dict[str, float] = {}
_lock = Lock()


def add(sessionid: str, role: str, text: str):
    """记录一轮对话。role 为 'user' 或 'assistant'。"""
    if not sessionid or not text:
        return
    with _lock:
        if sessionid not in _store:
            _store[sessionid] = deque(maxlen=MAX_ROUNDS * 2)
        _store[sessionid].append((role, text))
        _timestamps[sessionid] = time.time()
        _cleanup_expired()


def get_context(sessionid: str, max_rounds: int = MAX_ROUNDS) -> str:
    """获取格式化的对话历史，用于注入 prompt。"""
    with _lock:
        if sessionid not in _store or not _store[sessionid]:
            return ""
        entries = list(_store[sessionid])[-(max_rounds * 2):]
        if not entries:
            return ""

    lines = ["【对话历史】"]
    for role, text in entries:
        label = "游客" if role == "user" else "数字人"
        lines.append(f"{label}：{text}")
    return "\n".join(lines)


def clear(sessionid: str):
    """清除指定会话。"""
    with _lock:
        _store.pop(sessionid, None)
        _timestamps.pop(sessionid, None)


def _cleanup_expired():
    """清理过期会话。"""
    now = time.time()
    expired = [sid for sid, ts in _timestamps.items() if now - ts > SESSION_TTL]
    for sid in expired:
        _store.pop(sid, None)
        _timestamps.pop(sid, None)
