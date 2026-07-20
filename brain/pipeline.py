"""景区导览数字人 核心流水线。

处理用户输入 → 根据意图分流（路线推荐 / RAG 问答 / 通用闲聊）→ 推流 LiveTalking。
"""
import json
import time

from brain.adapter.livetalking_bridge import send_text
from brain.llm_client import chat

# ── POI 坐标库（视觉定位用）───────────────────────────────
POI_COORDS = {
    "灵山大佛": (120.0964, 31.4303),
    "梵宫": (120.1024, 31.4289),
    "五印坛城": (120.1030, 31.4248),
    "九龙灌浴": (120.1001, 31.4248),
    "拈花湾": (120.0765, 31.4193),
    "天下第一掌": (120.0970, 31.4295),
    "曼飞龙塔": (120.0990, 31.4300),
    "灵山博物馆": (120.1000, 31.4230),
    "百子戏弥勒": (120.1020, 31.4265),
    "阿育王柱": (120.1030, 31.4280),
    "灵山花海": (120.1030, 31.4220),
    "禅意小镇": (120.0775, 31.4180),
}

# ── 意图识别 ───────────────────────────────────────────

ROUTE_KEYWORDS = ["路线", "怎么逛", "怎么玩", "一日游",
                   "半日游", "先去", "再去", "游览顺序"]
ROUTE_COMBO_KEYWORDS = ["推荐", "行程", "规划"]  # 需配合路线类词

RAG_KEYWORDS = ["历史", "文化", "特色", "介绍", "背景", "典故", "传说",
                 "门票", "价格", "开放", "时间", "怎么去", "地址",
                 "建筑", "佛像", "佛教", "禅", "景点", "灵山",
                 "大佛", "梵宫", "拈花湾", "坛城", "九龙",
                 "消费", "预算", "花费", "费用", "多少钱", "玩几天"]

LOCATE_KEYWORDS = ["我在哪", "这是哪", "定位", "这里是什么地方", "我在哪里",
                    "这是什么地方", "定位一下", "我在什么位置"]


def _is_route_intent(text: str) -> bool:
    """路线意图：核心词直接命中，或组合词+路线类词同时出现。"""
    has_core = any(k in text for k in ROUTE_KEYWORDS)
    has_combo = any(k in text for k in ROUTE_COMBO_KEYWORDS)
    route_context = any(k in text for k in ["路线", "游览", "逛", "玩"])
    return has_core or (has_combo and route_context)


def _is_rag_intent(text: str) -> bool:
    """知识问答意图。"""
    return any(k in text for k in RAG_KEYWORDS)


def _is_locate_intent(text: str) -> bool:
    """定位意图。"""
    return any(k in text for k in LOCATE_KEYWORDS)


# ── 意图处理函数 ────────────────────────────────────────

def _handle_route(text: str) -> str:
    """处理路线推荐意图。"""
    from brain.skills.route_recommender import recommend, list_interests

    interests = list_interests()
    matched_interest = "综合"
    for tag in interests:
        if tag in text:
            matched_interest = tag
            break

    duration = 4
    for word in ["半天", "半日"]:
        if word in text:
            duration = 4
            break
    for word in ["一天", "一日", "全天"]:
        if word in text:
            duration = 8
            break

    rec = recommend(interest=matched_interest, duration_hours=duration)

    if not rec.get("route"):
        return chat(f"请为游客推荐一条游览路线。游客偏好：{text}")

    spots = "\n".join(
        f"- {p['name']}（约{p['dwell_min']}分钟，{p['reason']}）"
        for p in rec["route"]
    )
    polish_prompt = (
        f"你是灵山胜境的真人导游。请根据以下景点列表，用亲切自然的口语为游客推荐一条"
        f"{rec['duration_hours']}小时『{matched_interest}』主题游览路线。\n\n"
        f"要求：\n"
        f"1. 用\"首先、接着、然后、最后\"等连接词串联景点\n"
        f"2. 每个景点附带一句简短介绍（1句话，体现景点特色）\n"
        f"3. 总字数不超过 150 字\n"
        f"4. 语气热情但不过度，像真人导游在说话\n\n"
        f"景点列表：\n{spots}"
    )
    return chat(polish_prompt)


def _handle_rag(text: str, history: str = "") -> str:
    """处理知识问答意图（RAG 增强）。"""
    from brain.rag.retriever import answer_with_rag
    result = answer_with_rag(text, history=history)
    return result["answer"]


def _handle_chat(text: str, image_path: str | None = None, image_base64: str | None = None, history: str = "") -> str:
    """通用闲聊（直接 LLM）。"""
    if history:
        text = f"{history}\n【当前问题】{text}"
    return chat(text, image_path=image_path, image_base64=image_base64)


def _handle_photo(text: str, image_base64: str, history: str = "") -> str:
    """拍照识景：多模态识别景点并讲解。"""
    prompt = text.strip() if text.strip() else "请识别这张照片中的景点，并为我详细介绍"
    full_prompt = (
        f"这张照片是游客在灵山胜境景区（无锡太湖之滨）拍摄的。"
        f"请仔细观察照片内容，识别这是哪个景点（如灵山大佛、灵山梵宫、拈花湾、"
        f"九龙灌浴、五印坛城、天下第一掌等），然后以数字人导游的身份，"
        f"用亲切自然的口语为游客详细介绍这个景点。"
        f"如果照片中没有明显的景区地标，请根据照片中的可见元素"
        f"（建筑风格、佛像、自然景观、标识物等）推测可能的景点并推荐游览信息。"
        f"\n\n游客说：{prompt}"
    )
    return chat(full_prompt, image_base64=image_base64)


def _handle_locate(text: str, image_base64: str) -> dict:
    """拍照定位：多模态识别景点并返回坐标（GPS 弱信号场景兜底）。"""
    poi_list = "\n".join(f"- {name}" for name in POI_COORDS)
    prompt = text.strip() if text.strip() else "这里是灵山胜境的哪个位置？"
    full_prompt = (
        f"这张照片是游客在灵山胜境景区拍摄的。请仔细观察照片中的地标、建筑、"
        f"雕塑、自然景观等视觉特征，判断这是景区的哪个具体位置。\n\n"
        f"景区有以下景点：\n{poi_list}\n\n"
        f"请用JSON格式回复（只返回JSON，不要其他文字）：\n"
        f'{{"landmark":"景点名称","message":"用一句话告诉游客他在哪里，距哪个景点最近"}}\n\n'
        f"游客说：{prompt}"
    )
    raw = chat(full_prompt, image_base64=image_base64)
    landmark, message = "", raw
    try:
        raw_clean = raw.strip()
        if "```" in raw_clean:
            raw_clean = raw_clean.split("```")[1]
            if raw_clean.startswith("json"):
                raw_clean = raw_clean[4:]
            raw_clean = raw_clean.strip()
        data = json.loads(raw_clean)
        landmark = data.get("landmark", "")
        message = data.get("message", raw)
    except (json.JSONDecodeError, IndexError):
        for name in POI_COORDS:
            if name in raw:
                landmark = name
                break
    lng, lat = POI_COORDS.get(landmark, (None, None))
    return {"reply": message, "landmark": landmark, "lat": lat, "lng": lng}


# ── 天气感知 ────────────────────────────────────────────
def _get_weather_context() -> str:
    """获取当前天气简报，注入 LLM prompt。"""
    try:
        import urllib.request, os
        from pathlib import Path
        import yaml
        cfg_path = Path(__file__).parent / "config" / "settings.yaml"
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))["weather"]
        api_key = os.getenv(cfg["api_key_env"], "")
        if not api_key:
            return ""
        lat, lng = cfg["lat"], cfg["lng"]
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={api_key}&units=metric&lang=zh_cn"
        with urllib.request.urlopen(url, timeout=3) as resp:
            raw = __import__("json").loads(resp.read())
        cond = raw["weather"][0]["description"]
        temp = round(raw["main"]["temp"])
        return f"【今日天气】{cond}，温度{temp}°C。如涉及户外景点（九龙灌浴、大佛登顶、拈花湾夜游等），请主动提醒游客天气影响并推荐室内替代（梵宫、博物馆等）。"
    except Exception:
        return ""  # 兜底：无天气信息时不注入


# ── 主入口 ──────────────────────────────────────────────

def handle_user_input(text: str, image_path: str | None = None, image_base64: str | None = None, sessionid: str = "") -> dict:
    """完整链路：意图分流 → 处理 → LiveTalking 推流。"""
    t0 = time.time()

    # 获取历史上下文
    from brain.memory import get_context, add as mem_add
    history = get_context(sessionid)

    # 有图片时根据文本意图分流：定位 or 拍照识景
    has_image = bool(image_path or image_base64)
    if has_image and _is_locate_intent(text):
        intent = "locate"
        result = _handle_locate(text, image_base64=image_base64 or "")
    elif has_image:
        intent = "photo"
        result = {"reply": _handle_photo(text, image_base64=image_base64 or "", history=history)}
    elif _is_locate_intent(text):
        intent = "locate"
        result = _handle_locate(text, image_base64="")
    elif _is_route_intent(text):
        intent = "route"
        weather_ctx = _get_weather_context()
        if weather_ctx:
            result = {"reply": _handle_route(weather_ctx + "\n" + text)}
        else:
            result = {"reply": _handle_route(text)}
    elif _is_rag_intent(text):
        intent = "rag"
        weather_ctx = _get_weather_context()
        if weather_ctx:
            result = {"reply": _handle_rag(weather_ctx + "\n" + text, history=history)}
        else:
            result = {"reply": _handle_rag(text, history=history)}
    else:
        intent = "chat"
        result = {"reply": _handle_chat(text, image_path=image_path, history=history)}

    reply = result.get("reply", "")

    # 记录对话
    if sessionid:
        mem_add(sessionid, "user", text)
        mem_add(sessionid, "assistant", reply)

    delivered = True
    if sessionid:
        # ponytail: 后台线程推 TTS，不阻塞文字回复返回
        import threading
        threading.Thread(target=send_text, args=(reply, sessionid), daemon=True).start()

    return {
        "reply": reply,
        "delivered": delivered,
        "latency_sec": round(time.time() - t0, 2),
        "intent": intent,
        "landmark": result.get("landmark", ""),
        "lat": result.get("lat"),
        "lng": result.get("lng"),
    }
