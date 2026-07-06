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

    today_qs = [l.content for l in today if l.role == "user"]
    hot = Counter(today_qs).most_common(5)

    satisfaction = []
    for i in range(6, -1, -1):
        day0 = (now - timedelta(days=i)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day1 = day0 + timedelta(days=1)
        day_logs = [
            l
            for l in week
            if l.role == "user" and day0 <= l.created_at < day1
        ]
        pos = sum(1 for l in day_logs if l.sentiment == "pos")
        total = max(len(day_logs), 1)
        satisfaction.append({
            "date": day0.strftime("%m-%d"),
            "satisfaction": round(pos / total, 2),
            "count": len(day_logs),
        })

    return {
        "today_count": len(today),
        "week_count": len(week),
        "hot_questions": [{"question": q, "count": c} for q, c in hot],
        "satisfaction_trend": satisfaction,
    }
