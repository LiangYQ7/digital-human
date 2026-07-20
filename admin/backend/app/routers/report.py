from datetime import datetime, timedelta
from collections import Counter

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.analyzer import (
    hourly_distribution, sentiment_counts, suggestions,
    top_keywords, topic_breakdown
)
from app.deps import get_db
from app.models import ChatLog

router = APIRouter(prefix="/api/report", tags=["report"])


class RatingRequest(BaseModel):
    session_id: str = ""
    rating: int  # 1-5
    comment: str = ""


@router.post("/rating")
def submit_rating(req: RatingRequest, db: Session = Depends(get_db)):
    """游客提交评分（1-5 星），记录到最近一次 AI 回复的 extra 字段。"""
    # 查找该 session 最近一次 assistant 消息
    log = (
        db.query(ChatLog)
        .filter(ChatLog.session_id == req.session_id, ChatLog.role == "assistant")
        .order_by(ChatLog.id.desc())
        .first()
    )
    if log:
        extra = dict(log.extra) if log.extra else {}
        extra["rating"] = req.rating
        extra["comment"] = req.comment
        log.extra = extra
        # 高评分更新情感
        if req.rating >= 4:
            log.sentiment = "pos"
        elif req.rating <= 2:
            log.sentiment = "neg"
        db.commit()
        return {"status": "ok", "updated_id": log.id}
    # 找不到对应 session，直接创建一条评价记录
    sid = req.session_id or f"rating_{datetime.utcnow().timestamp()}"
    db.add(ChatLog(
        session_id=sid, role="assistant",
        content=f"游客评价: {req.rating} 星",
        latency_sec=0,
        sentiment="pos" if req.rating >= 4 else ("neg" if req.rating <= 2 else "neu"),
        extra={"rating": req.rating, "comment": req.comment, "type": "rating"},
    ))
    db.commit()
    return {"status": "ok", "note": "created new rating entry"}


@router.get("/insights")
def insights(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    logs = db.query(ChatLog).filter(ChatLog.created_at >= since).all()
    user_msgs = [l for l in logs if l.role == "user"]
    assistant_msgs = [l for l in logs if l.role == "assistant"]

    # 情感分布（AI 回复）
    sent = sentiment_counts(assistant_msgs)
    # 关键词（jieba 分词）
    kw = top_keywords([l.content for l in user_msgs])
    # 时段分布
    hourly = hourly_distribution(user_msgs)
    # 主题分布
    topics = topic_breakdown(user_msgs)
    # 热门问题
    q_counter = Counter(l.content for l in user_msgs)
    hot = [{"question": q, "count": c} for q, c in q_counter.most_common(10)]
    # 平均延迟
    avg_latency = (
        round(sum(l.latency_sec for l in assistant_msgs) / max(len(assistant_msgs), 1), 2)
        if assistant_msgs else 0
    )

    return {
        "range_days": days,
        "total_interactions": len(user_msgs),
        "avg_latency_sec": avg_latency,
        "top_keywords": kw,
        "sentiment_trend": sent,
        "hourly_distribution": hourly,
        "topic_breakdown": topics,
        "hot_questions": hot,
        "suggestions": suggestions(kw, sent),
    }


@router.post("/ai-summary")
def ai_summary(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """调用 LLM 生成运营洞察总结（临时展示，刷新后消失）。"""
    since = datetime.utcnow() - timedelta(days=days)
    logs = db.query(ChatLog).filter(ChatLog.created_at >= since).all()
    user_msgs = [l for l in logs if l.role == "user"]
    assistant_msgs = [l for l in logs if l.role == "assistant"]

    sent = sentiment_counts(assistant_msgs)
    kw = top_keywords([l.content for l in user_msgs])
    topics = topic_breakdown(user_msgs)
    hourly = hourly_distribution(user_msgs)
    neg_ratio = sent.get("neg", 0) / max(sum(sent.values()), 1)

    # 高峰时段
    peak = sorted(hourly, key=lambda x: -x["count"])[:3]
    peak_str = "、".join(f"{p['hour']}({p['count']}次)" for p in peak if p["count"] > 0)

    prompt = (
        f"你是灵山胜境景区的运营数据分析师，语气轻松像朋友聊天。\n"
        f"根据以下近{days}天数据，写一段180字以内的运营洞察：\n"
        f"- 游客交互：{len(user_msgs)}条消息\n"
        f"- 情感：正面{sent.get('pos',0)} 中性{sent.get('neutral',0)} 负面{sent.get('neg',0)}\n"
        f"- 热门关键词：{', '.join(k['word'] for k in kw[:6])}\n"
        f"- 关注主题：{', '.join(t['topic']+str(t['count'])+'次' for t in topics[:4])}\n"
        f"- 高峰时段：{peak_str or '暂无'}\n"
        f"- 负面占比：{neg_ratio:.0%}\n"
        f"要求：以「嘿，看了下最近的数据」开头；亮点+关注点各1-2句；结尾1条具体建议；轻松口吻。"
    )

    try:
        from brain.llm_client import chat as _llm_chat
        summary = _llm_chat(prompt)
    except Exception as e:
        summary = f"AI 总结生成失败：{e}"

    return {"summary": summary, "prompt_used": prompt}
