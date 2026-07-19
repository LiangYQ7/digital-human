from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import ChatLog

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    today = db.query(ChatLog).filter(ChatLog.created_at >= today0).all()
    week = db.query(ChatLog).filter(ChatLog.created_at >= week_ago).all()

    # 热门问题（用户消息）
    today_qs = [l.content for l in today if l.role == "user"]
    hot = Counter(today_qs).most_common(5)

    # 今日/本周服务人次（按独立会话数，不是消息数）
    today_sessions = len(set(l.session_id for l in today))
    week_sessions = len(set(l.session_id for l in week))

    # 满意度趋势（只看AI回复的情感）
    satisfaction = []
    for i in range(6, -1, -1):
        day0 = (now - timedelta(days=i)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day1 = day0 + timedelta(days=1)
        day_logs = [
            l
            for l in week
            if l.role == "assistant" and day0 <= l.created_at < day1
        ]
        pos = sum(1 for l in day_logs if l.sentiment == "pos")
        total = max(len(day_logs), 1)
        satisfaction.append({
            "date": day0.strftime("%m-%d"),
            "satisfaction": round(pos / total, 2),
            "count": len(day_logs),
        })

    return {
        "today_count": today_sessions,
        "week_count": week_sessions,
        "hot_questions": [{"question": q, "count": c} for q, c in hot],
        "satisfaction_trend": satisfaction,
    }
