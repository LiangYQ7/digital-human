import re
from collections.abc import Counter as CounterType
from typing import Any


def top_keywords(messages: list[str], n: int = 10) -> list[dict]:
    """简易中文关键词：2-4 字滑窗 + 停用词。生产可换 jieba。"""
    stop: set[str] = {
        "怎么", "什么", "怎么买", "你好", "请问",
        "我们", "可以", "这个", "那个", "一个",
        "就是", "没有", "不是", "还是", "因为",
        "所以", "如果", "但是", "而且", "或者",
    }
    counter: CounterType[str] = CounterType()
    for msg in messages:
        for size in (2, 3, 4):
            for i in range(len(msg) - size + 1):
                w = msg[i : i + size]
                if w in stop or re.search(r"[，。？！,. ]", w):
                    continue
                counter[w] += 1
    return [{"word": w, "count": c} for w, c in counter.most_common(n)]


def sentiment_counts(logs: list) -> dict:
    out = {"pos": 0, "neu": 0, "neg": 0}
    for l in logs:
        if l.sentiment in out:
            out[l.sentiment] += 1
    return out


def suggestions(keywords: list[dict], sentiment: dict) -> list[str]:
    tips: list[str] = []
    if sentiment.get("neg", 0) > sentiment.get("pos", 0):
        tips.append("负面反馈偏高，建议核查服务流程")
    for k in keywords[:3]:
        if "票" in k["word"] or "门票" in k["word"]:
            tips.append(
                f"游客高频关注『{k['word']}』，建议在导览首屏主动告知购票信息"
            )
    if not tips:
        tips.append("整体反馈平稳，可增加互动性讲解提升体验")
    return tips
