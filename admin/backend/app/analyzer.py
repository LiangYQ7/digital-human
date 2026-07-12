import re
from collections import Counter
from typing import Any


def top_keywords(messages: list[str], n: int = 10) -> list[dict]:
    """简易中文关键词：2-4 字滑窗 + 停用词。生产可换 jieba。"""
    stop: set[str] = {
        "怎么", "什么", "怎么买", "你好", "请问",
        "我们", "可以", "这个", "那个", "一个",
        "一下", "没有", "还是", "如果", "因为",
        "现在", "已经", "或者", "不过", "但是",
    }
    counter: Counter[str] = Counter()
    for msg in messages:
        for size in (2, 3, 4):
            for i in range(len(msg) - size + 1):
                w = msg[i : i + size]
                if w not in stop:
                    counter[w] += 1
    return [
        {"word": w, "count": c}
        for w, c in counter.most_common(n)
    ]


def sentiment_counts(logs: list) -> dict:
    """统计正面/中性/负面情绪数量。"""
    pos = sum(1 for l in logs if getattr(l, "sentiment", "") == "pos")
    neg = sum(1 for l in logs if getattr(l, "sentiment", "") == "neg")
    neutral = len(logs) - pos - neg
    return {"pos": pos, "neutral": neutral, "neg": neg}


def suggestions(keywords: list[dict], sentiment: dict) -> list[str]:
    """根据关键词和情感生成运营建议。"""
    tips: list[str] = []
    total = sentiment.get("pos", 0) + sentiment.get("neutral", 0) + sentiment.get("neg", 0)
    if total == 0:
        return ["暂无足够的游客交互数据，建议增加互动引导。"]

    neg_ratio = sentiment.get("neg", 0) / max(total, 1)
    top_words = [k["word"] for k in keywords[:5]]

    if neg_ratio > 0.3:
        tips.append(f"负面情绪占比 {neg_ratio:.0%}，建议排查游客不满原因并优化服务。")
    if any(w in top_words for w in ["门票", "价格", "费用"]):
        tips.append("游客对价格较关注，考虑推出套票或多时段优惠活动。")
    if any(w in top_words for w in ["路线", "游玩", "推荐"]):
        tips.append("路线相关提问较多，可在知识库中丰富游览攻略内容。")
    if any(w in top_words for w in ["时间", "开放", "几点"]):
        tips.append("开放时间类提问高频，建议在显著位置公示营业时间。")
    if not tips:
        tips.append("游客反馈整体良好，继续保持现有服务质量。")

    return tips
