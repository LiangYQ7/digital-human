"""个性化路线推荐引擎。

根据游客兴趣偏好（如"喜欢历史"/"喜欢自然风光"），结合景区 POI 数据，
推荐游览路线和讲解重点。
"""
import json
from pathlib import Path

_POIS: list[dict] | None = None


def _load_pois() -> list[dict]:
    """加载景区 POI 数据。"""
    global _POIS
    if _POIS is None:
        poi_path = Path(__file__).parent.parent / "data" / "scenic_pois.json"
        if poi_path.exists():
            _POIS = json.loads(poi_path.read_text(encoding="utf-8")).get("pois", [])
        else:
            _POIS = []
    return _POIS


def _score_poi(poi: dict, interest: str) -> float:
    """根据兴趣标签匹配度 + 必看加权打分。"""
    score = 0.0
    tags = [t.lower() for t in poi.get("tags", [])]
    interest_lower = interest.lower()

    # 标签直接匹配
    if interest_lower in tags:
        score += 3.0
    # 部分匹配
    for tag in tags:
        if interest_lower in tag or tag in interest_lower:
            score += 1.5

    # 必看景点加权
    if poi.get("must_see"):
        score += 2.0

    return score


def recommend(interest: str = "综合", duration_hours: int = 4) -> dict:
    """推荐游览路线。

    Args:
        interest: 兴趣偏好，如"历史"、"自然风光"、"建筑"、"佛教文化"、"综合"
        duration_hours: 预估游览时长（小时）

    Returns:
        {
            "route": [{"name": str, "reason": str, "dwell_min": int}, ...],
            "duration_hours": int,
            "total_min": int,
            "interest": str,
        }
    """
    pois = _load_pois()
    if not pois:
        return {
            "route": [],
            "duration_hours": duration_hours,
            "total_min": 0,
            "interest": interest,
            "fallback": True,
        }

    budget_min = duration_hours * 60

    # 按兴趣得分降序
    scored = sorted(pois, key=lambda p: _score_poi(p, interest), reverse=True)

    route = []
    used = 0
    for poi in scored:
        dwell = poi.get("dwell_min", 20)
        if used + dwell > budget_min:
            continue
        tags = poi.get("tags", [])
        is_must = poi.get("must_see", False)
        reason_parts = []
        if is_must:
            reason_parts.append("必看景点")
        match_tags = [t for t in tags if interest in t or t in interest]
        if match_tags:
            reason_parts.append(f"契合『{interest}』兴趣")
        if not reason_parts:
            reason_parts.append("推荐游览")

        route.append({
            "name": poi["name"],
            "reason": " · ".join(reason_parts),
            "dwell_min": dwell,
        })
        used += dwell

    # 如果兴趣过于小众导致路线太短，尝试补一个必看景点（但不能超预算）
    if len(route) < 2:
        for poi in pois:
            if (poi.get("must_see") and
                    poi["name"] not in [r["name"] for r in route] and
                    used + poi.get("dwell_min", 20) <= budget_min):
                route.append({
                    "name": poi["name"],
                    "reason": "必看景点（推荐）",
                    "dwell_min": poi.get("dwell_min", 20),
                })
                used += poi.get("dwell_min", 20)
                break

    return {
        "route": route,
        "duration_hours": duration_hours,
        "total_min": used,
        "interest": interest,
    }


def list_pois() -> list[dict]:
    """列出所有景区 POI。"""
    return _load_pois()


def list_interests() -> list[str]:
    """列出所有可选兴趣标签。"""
    pois = _load_pois()
    tags_set: set[str] = set()
    for poi in pois:
        for tag in poi.get("tags", []):
            tags_set.add(tag)
    return sorted(tags_set)
