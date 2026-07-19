"""游客数据分析引擎 — 关键词提取 / 情感统计 / 智能建议。"""
from collections import Counter
from typing import Any

import jieba

# 停用词（过滤无意义的常见词）
_STOP = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不",
    "人", "都", "一", "一个", "上", "也", "很", "到", "说",
    "要", "去", "你", "会", "着", "没有", "看", "好", "自己",
    "这", "他", "她", "它", "们", "那", "吗", "吧", "啊",
    "哦", "嗯", "呢", "呀", "哈", "嘛", "啦", "什么", "怎么",
    "如何", "哪", "多少", "为什么", "请问", "你好", "谢谢",
    "这个", "那个", "可以", "还是", "如果", "因为", "现在",
    "已经", "或者", "不过", "但是", "然后", "所以", "虽然",
    "我们", "他们", "这里", "那里", "就是", "觉得", "知道",
    "需要", "应该", "可能", "比较", "非常", "真的", "主要",
}

# 有用关键词白名单（景区/旅游相关，确保不被过滤）
_KEEP = {
    "门票", "价格", "开放", "时间", "路线", "推荐", "交通",
    "停车", "吃饭", "餐厅", "素斋", "导游", "讲解", "表演",
    "历史", "文化", "建筑", "佛教", "佛像", "禅", "景点",
    "灵山", "大佛", "梵宫", "拈花湾", "坛城", "九龙",
    "消费", "预算", "花费", "费用", "攻略", "游玩",
    "拍照", "打卡", "夜景", "花海", "博物馆", "雕塑",
    "登顶", "祈福", "摸掌", "体验", "联票", "半价",
    "学生", "老人", "儿童", "免费", "公交", "地铁",
    "自驾", "停车费", "寄存", "行李", "轮椅", "母婴",
    # 景区专有名词
    "五印坛城", "天下第一掌", "灵山博物馆", "九龙灌浴",
    "百子戏弥勒", "阿育王柱", "曼飞龙塔", "禅意小镇",
    "梵天花海", "灵山花海", "灵山胜境", "灵山大佛",
    "藏传佛教", "唐卡", "转经筒", "金顶", "弥勒",
}

# 注入景区专有名词，确保 jieba 正确切分
for _word in _KEEP:
    if len(_word) >= 3:
        jieba.add_word(_word)


def top_keywords(messages: list[str], n: int = 15) -> list[dict]:
    """使用 jieba 分词提取高频关键词，过滤停用词，保留有用词汇。"""
    counter: Counter[str] = Counter()
    for msg in messages:
        words = jieba.cut(msg)
        for w in words:
            w = w.strip()
            if len(w) < 2:
                continue
            if w in _KEEP:
                counter[w] += 2  # 白名单加权
            elif w not in _STOP:
                counter[w] += 1
    return [
        {"word": w, "count": c}
        for w, c in counter.most_common(n)
        if len(w) >= 2
    ]


def sentiment_counts(logs: list) -> dict:
    """统计 AI 回复的情感分布。"""
    pos = sum(1 for l in logs if getattr(l, "sentiment", "") == "pos")
    neg = sum(1 for l in logs if getattr(l, "sentiment", "") == "neg")
    total = len(logs)
    neutral = total - pos - neg
    return {"pos": pos, "neutral": max(0, neutral), "neg": neg}


def hourly_distribution(logs: list) -> list[dict]:
    """统计按小时分布的服务量。"""
    hours = Counter()
    for l in logs:
        if hasattr(l, "created_at") and l.created_at:
            hours[l.created_at.hour] += 1
    return [{"hour": f"{h:02d}:00", "count": hours.get(h, 0)} for h in range(24)]


def topic_breakdown(logs: list) -> list[dict]:
    """按主题分类统计游客关注点。"""
    topics = {
        "门票价格": ["门票", "票价", "价格", "多少钱", "费用", "收费", "半价", "免费"],
        "交通出行": ["怎么去", "公交", "地铁", "自驾", "停车", "交通", "打车"],
        "景点特色": ["景点", "特色", "介绍", "历史", "文化", "建筑", "雕塑"],
        "餐饮服务": ["吃饭", "餐厅", "素斋", "小吃", "美食", "喝水"],
        "游玩攻略": ["路线", "攻略", "推荐", "行程", "一日游", "半天", "怎么玩"],
        "表演活动": ["表演", "演出", "灯光", "夜游", "秀"],
    }
    result = []
    for topic, keywords in topics.items():
        count = sum(1 for l in logs if any(k in getattr(l, "content", "") for k in keywords))
        result.append({"topic": topic, "count": count})
    result.sort(key=lambda x: x["count"], reverse=True)
    return result


def suggestions(keywords: list[dict], sentiment: dict) -> list[str]:
    """根据关键词和情感生成运营建议。"""
    tips: list[str] = []
    total = sentiment.get("pos", 0) + sentiment.get("neutral", 0) + sentiment.get("neg", 0)
    if total == 0:
        return ["暂无足够的游客交互数据，建议增加互动引导。"]

    neg_ratio = sentiment.get("neg", 0) / max(total, 1)
    top_words = [k["word"] for k in keywords[:8]]

    if neg_ratio > 0.25:
        tips.append(f"负面评价占比 {neg_ratio:.0%}，建议排查游客不满原因并优化服务体验。")
    elif neg_ratio < 0.1:
        tips.append(f"游客满意度良好，负面评价仅 {neg_ratio:.0%}，继续保持服务质量。")

    if any(w in top_words for w in ["门票", "价格", "费用", "收费"]):
        tips.append("游客对门票价格关注度较高，可考虑推出家庭套票、早鸟票等优惠政策。")
    if any(w in top_words for w in ["路线", "攻略", "推荐"]):
        tips.append("路线规划需求旺盛，建议在公众号增加自助路线推荐功能。")
    if any(w in top_words for w in ["停车", "交通", "公交"]):
        tips.append("交通类问题咨询量大，建议优化停车场指引和公共交通信息展示。")
    if any(w in top_words for w in ["表演", "活动", "灯光", "夜游"]):
        tips.append("表演活动受关注，可增加场次预告推送，提升游客参与度。")
    if any(w in top_words for w in ["吃饭", "餐厅", "素斋", "美食"]):
        tips.append("餐饮信息需求旺盛，建议完善景区内餐饮指南并标注特色菜品。")

    if not tips:
        tips.append("整体运营正常，建议持续关注游客反馈并丰富知识库内容。")

    return tips
