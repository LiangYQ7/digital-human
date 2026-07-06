from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analyzer import sentiment_counts, suggestions, top_keywords
from app.deps import get_db
from app.models import ChatLog

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/insights")
def insights(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    logs = db.query(ChatLog).filter(ChatLog.created_at >= since).all()
    user_msgs = [l.content for l in logs if l.role == "user"]
    kw = top_keywords(user_msgs)
    sent = sentiment_counts(logs)
    return {
        "range_days": days,
        "total_interactions": len(logs),
        "top_keywords": kw,
        "sentiment_trend": sent,
        "suggestions": suggestions(kw, sent),
    }
