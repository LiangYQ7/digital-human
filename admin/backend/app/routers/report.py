from datetime import datetime, timedelta
from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analyzer import (
    hourly_distribution, sentiment_counts, suggestions,
    top_keywords, topic_breakdown
)
from app.deps import get_db
from app.models import ChatLog

router = APIRouter(prefix="/api/report", tags=["report"])


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
