"""景区导览数字人 核心流水线。

处理用户输入 → 根据意图分流（路线推荐 / RAG 问答 / 通用闲聊）→ 推流 LiveTalking。
"""
import time

from brain.adapter.livetalking_bridge import send_text
from brain.llm_client import chat

# ── 意图识别 ───────────────────────────────────────────

ROUTE_KEYWORDS = ["路线", "怎么逛", "怎么玩", "一日游",
                   "半日游", "先去", "再去", "游览顺序"]
ROUTE_COMBO_KEYWORDS = ["推荐", "行程", "规划"]  # 需配合路线类词

RAG_KEYWORDS = ["历史", "文化", "特色", "介绍", "背景", "典故", "传说",
                 "门票", "价格", "开放", "时间", "怎么去", "地址",
                 "建筑", "佛像", "佛教", "禅", "景点", "灵山",
                 "大佛", "梵宫", "拈花湾", "坛城", "九龙",
                 "消费", "预算", "花费", "费用", "多少钱", "玩几天"]


def _is_route_intent(text: str) -> bool:
    """路线意图：核心词直接命中，或组合词+路线类词同时出现。"""
    has_core = any(k in text for k in ROUTE_KEYWORDS)
    has_combo = any(k in text for k in ROUTE_COMBO_KEYWORDS)
    route_context = any(k in text for k in ["路线", "游览", "逛", "玩"])
    return has_core or (has_combo and route_context)


def _is_rag_intent(text: str) -> bool:
    """知识问答意图。"""
    return any(k in text for k in RAG_KEYWORDS)


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


def _handle_chat(text: str, image_path: str | None = None, history: str = "") -> str:
    """通用闲聊（直接 LLM）。"""
    if history:
        text = f"{history}\n【当前问题】{text}"
    return chat(text, image_path=image_path)


# ── 主入口 ──────────────────────────────────────────────

def handle_user_input(text: str, image_path: str | None = None, sessionid: str = "") -> dict:
    """完整链路：意图分流 → 处理 → LiveTalking 推流。"""
    t0 = time.time()

    # 获取历史上下文
    from brain.memory import get_context, add as mem_add
    history = get_context(sessionid)

    if _is_route_intent(text):
        intent = "route"
        reply = _handle_route(text)
    elif _is_rag_intent(text):
        intent = "rag"
        reply = _handle_rag(text, history=history)
    else:
        intent = "chat"
        reply = _handle_chat(text, image_path=image_path, history=history)

    # 记录对话
    if sessionid:
        mem_add(sessionid, "user", text)
        mem_add(sessionid, "assistant", reply)

    delivered = send_text(reply, sessionid) if sessionid else False

    return {
        "reply": reply,
        "delivered": delivered,
        "latency_sec": round(time.time() - t0, 2),
        "intent": intent,
    }
