"""种子数据生成器 — 为管理后台生成 7 天模拟历史对话数据。

覆盖：数据大屏（今日/本周服务人次、满意度、热门问答、趋势、时段分布、主题分布）
      游客报告（情感分布、关键词、时段分布、主题分布、热门问题、运营建议）

运行: python brain/seed_data.py
"""
import os
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

# 加载 .env 中的配置（如 SQLITE_PATH）
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# 确保项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "admin" / "backend"))

from app.database import SessionLocal, engine, Base
from app.models import ChatLog

Base.metadata.create_all(bind=engine)

# ── 种子配置 ──
TOTAL_SESSIONS = 120          # 总独立会话数
DAYS = 7                      # 覆盖近 7 天
now = datetime.utcnow()

# ── 模拟对话模板 ──
user_questions = [
    # 门票价格
    ("门票多少钱？", "成人票210元，学生和老人半价105元。"),
    ("有没有家庭套票？", "目前暂无双人/家庭套票，建议关注景区公众号获取优惠信息。"),
    ("灵山胜境和拈花湾联票有优惠吗？", "有联票！含灵山胜境和拈花湾，价格约280元，比单独购票更划算。"),
    # 交通出行
    ("怎么去灵山胜境？", "公交88路/89路直达；自驾导航搜「灵山胜境」，景区有大型停车场。"),
    ("停车场收费吗？", "景区停车场收费10元/次，建议早点到，旺季车位紧张。"),
    ("从无锡火车站打车要多久？", "约40-50分钟，费用60-80元左右。"),
    # 景点特色
    ("灵山大佛有多高？", "通高88米！世界最高铜佛像之一，内部有电梯可达佛脚平台。"),
    ("梵宫好玩吗？", "梵宫是必看的！7.2万平米佛教艺术殿堂，金碧辉煌，珍宝馆藏品众多。"),
    ("拈花湾有什么特色？", "禅意小镇，唐风宋韵！3万平米花海、夜游灯光秀、禅修体验，建议傍晚去。"),
    ("九龙灌浴表演几点？", "每天10:00 / 13:00 / 15:00，建议提前10分钟到场占好位置。"),
    ("五印坛城是什么？", "藏传佛教风格建筑，有坛城金顶、转经筒、唐卡壁画，感受雪域文化。"),
    ("天下第一掌能摸吗？", "可以！摸掌祈福，沾福气保平安，是游客必打卡点～"),
    # 游玩攻略
    ("推荐一条半天路线", "建议：九龙灌浴→大佛→梵宫→拈花湾，约4小时。"),
    ("一天能逛完吗？", "深度游建议一整天：上午大佛+梵宫+坛城，下午九龙灌浴+博物馆，傍晚拈花湾夜游。"),
    ("带老人小孩怎么玩？", "推荐轻松路线：大佛（电梯登顶）→梵宫→博物馆，约3小时，不走太多路。"),
    # 表演活动
    ("夜游灯光秀几点开始？", "拈花湾夜游19:30开始，建议18:30到达，先逛花海再等灯光秀。"),
    # 餐饮服务
    ("景区有素斋吗？", "梵宫和博物馆旁都有素斋，推荐「灵山素斋」，人均30-50元。"),
    ("附近有什么好吃的？", "马山镇上有太湖三白（白鱼白虾银鱼），还有无锡小笼包和酱排骨。"),
    # 其他
    ("景区开放时间是？", "夏季7:00-17:30，冬季7:30-16:00，全年开放（恶劣天气除外）。"),
    ("可以寄存行李吗？", "景区入口有免费寄存柜，大件行李可寄存在游客中心。"),
]

# 问题关键词映射（用于情感判断）
pos_keywords = ["精彩", "好漂亮", "太棒", "很不错", "感谢", "喜欢", "好看", "震撼", "宏伟", "壮观"]
neg_keywords = ["失望", "有点贵", "太挤", "排队", "累了", "不好", "坑", "后悔"]

def gen_sentiment(reply: str) -> str:
    """合理的情感分布：~65% 正面, ~25% 中性, ~10% 负面"""
    r = random.random()
    # 大部分 AI 回答是正面体验
    if r < 0.65:
        return "pos"
    elif r < 0.90:
        return "neu"
    else:
        # 偶尔有负面（排队久 / 票价贵 / 天气不好）
        if random.random() < 0.5:
            return "neg"
        return "neu"

# 为热门问题增加更多种类和不同频次
def _weighted_question():
    """返回 (question, answer)，高频问题优先被选中"""
    weights = [5,3,4, 4,5,3, 8,7,8,9,4,3, 6,5,4, 3, 4,3, 5,4]  # 各问题的权重
    total = sum(weights)
    r = random.randint(1, total)
    acc = 0
    for i, w in enumerate(weights):
        acc += w
        if r <= acc:
            return user_questions[i]
    return user_questions[0]

# ── 生成数据 ──
db = SessionLocal()
try:
    existing = db.query(ChatLog).count()
    if existing > 20:
        # 强制重新生成：清空旧数据
        print(f"数据库已有 {existing} 条记录，正在清空并重新生成...")
        db.query(ChatLog).delete()
        db.commit()

    count = 0
    session_ids = [f"seed_{i:04d}_{random.randint(1000,9999)}" for i in range(TOTAL_SESSIONS)]

    for sid in session_ids:
        # 随机 1-3 轮对话
        rounds = random.choices([1, 2, 3], weights=[0.4, 0.35, 0.25])[0]
        base_time = now - timedelta(
            days=random.randint(0, DAYS - 1),
            hours=random.randint(7, 21),
            minutes=random.randint(0, 59),
        )

        for r in range(rounds):
            q, a = _weighted_question()
            t = base_time + timedelta(seconds=r * random.randint(3, 15))

            # 用户消息
            db.add(ChatLog(
                session_id=sid, role="user", content=q, latency_sec=0,
                sentiment="neu", created_at=t,
                extra={"round": r + 1}
            ))

            # AI 回复
            lat = random.randint(1, 4)  # 1-4秒延迟
            sent = gen_sentiment(a)
            db.add(ChatLog(
                session_id=sid, role="assistant", content=a,
                latency_sec=lat, sentiment=sent,
                created_at=t + timedelta(seconds=lat),
                extra={"intent": "rag" if any(k in q for k in ["历史","特色","介绍","门票","开放","时间","怎么去","建筑","佛像","表演","多高","什么"]) else "chat"}
            ))
            count += 2

    # 额外：生成一些带评价的记录（extra 中存储 rating）
    for _ in range(30):
        q, a = _weighted_question()
        sid = random.choice(session_ids)
        q_idx = None  # not used
        t = base_time = now - timedelta(
            days=random.randint(0, DAYS - 1),
            hours=random.randint(9, 20),
        )
        rating = random.randint(3, 5)
        db.add(ChatLog(
            session_id=sid, role="assistant", content=a,
            latency_sec=random.randint(1, 3), sentiment="pos",
            created_at=t,
            extra={"intent": "rag", "rating": rating,
                   "comment": random.choice(["", "讲解很详细！", "回复很及时", "态度很好", "非常满意"])}
        ))
        count += 1

    db.commit()
    print(f"种子数据已生成：{count} 条 ChatLog 记录，{TOTAL_SESSIONS} 个独立会话")

    # 追加今日数据（确保今天有统计）
    today_sessions = 15
    today_count = 0
    for i in range(today_sessions):
        sid = f"today_{i:03d}"
        q, a = _weighted_question()
        t = now - timedelta(minutes=random.randint(5, 240))  # 今天0-4小时前
        db.add(ChatLog(session_id=sid, role="user", content=q, latency_sec=0,
                        sentiment="neu", created_at=t, extra={"round": 1}))
        lat = random.randint(1, 3)
        sent = gen_sentiment(a)
        db.add(ChatLog(session_id=sid, role="assistant", content=a,
                        latency_sec=lat, sentiment=sent,
                        created_at=t + timedelta(seconds=lat),
                        extra={"intent": "rag"}))
        today_count += 2

        # 随机追加第2轮
        if random.random() < 0.4:
            q2, a2 = _weighted_question()
            t2 = t + timedelta(seconds=random.randint(10, 60))
            db.add(ChatLog(session_id=sid, role="user", content=q2, latency_sec=0,
                            sentiment="neu", created_at=t2, extra={"round": 2}))
            db.add(ChatLog(session_id=sid, role="assistant", content=a2,
                            latency_sec=random.randint(1, 3), sentiment=gen_sentiment(a2),
                            created_at=t2 + timedelta(seconds=random.randint(1, 3)),
                            extra={"intent": "chat"}))
            today_count += 2

    db.commit()
    print(f"追加今日数据：{today_count} 条 ({today_sessions} 个会话)")
    print(f"覆盖 {DAYS} 天，时段 7:00-22:00")
    print(f"包含门票/交通/景点/攻略/表演/餐饮等 6 大主题")
    print(f"可直接刷新管理后台查看数据大屏和游客报告")

finally:
    db.close()
