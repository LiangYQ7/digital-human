"""从灵山.xlsx提取游客消费统计摘要，写入 brain/data/raw 供 RAG 入库"""
from pathlib import Path
import pandas as pd

xlsx_path = Path(r"D:\20260323113204906\示范景区公开资料包\灵山.xlsx")
out_path = Path(r"D:\Code\Vs code\digital_human\brain\data\raw\灵山游客消费统计.txt")

df = pd.read_excel(xlsx_path)

# ── 全局统计 ──
total = len(df)
lines = [
    "游客实际消费统计数据（基于777条真实游客消费记录）",
    f"数据来源：灵山胜境景区（含灵山大佛、拈花湾）游客消费调研",
    "",
    "【总体消费概况】",
    f"- 统计游客数：{total}人",
    f"- 平均停留时长：{df['stay_duration'].mean():.1f}小时",
    f"- 平均同行人数：{df['group_size'].mean():.1f}人",
    f"- 人均总消费：{df['total_cost'].mean():.0f}元（中位数{df['total_cost'].median():.0f}元，范围{df['total_cost'].min():.0f}-{df['total_cost'].max():.0f}元）",
    f"- 满意度均分：{df['satisfaction'].mean():.1f}/5",
    "",
    "【分项人均消费】",
    f"- 门票：平均{df['ticket_cost'].mean():.0f}元（多数{df['ticket_cost'].mode().values[0]:.0f}元）",
    f"- 餐饮：平均{df['food_cost'].mean():.0f}元（范围{df['food_cost'].min():.0f}-{df['food_cost'].max():.0f}元）",
    f"- 购物：平均{df['shopping_cost'].mean():.0f}元（范围{df['shopping_cost'].min():.0f}-{df['shopping_cost'].max():.0f}元）",
    f"- 交通：平均{df['transport_cost'].mean():.0f}元",
    f"- 娱乐：平均{df['entertainment_cost'].mean():.0f}元",
]

# ── 按景区拆分 ──
for name in df['attraction_name'].unique():
    sub = df[df['attraction_name'] == name]
    lines.append("")
    lines.append(f"【{name} 专项统计】（{len(sub)}人）")
    lines.append(f"- 平均停留：{sub['stay_duration'].mean():.1f}小时")
    lines.append(f"- 人均总消费：{sub['total_cost'].mean():.0f}元")
    lines.append(f"- 人均门票：{sub['ticket_cost'].mean():.0f}元")
    lines.append(f"- 人均餐饮：{sub['food_cost'].mean():.0f}元")
    lines.append(f"- 人均购物：{sub['shopping_cost'].mean():.0f}元")

# ── 同行人数消费对比 ──
lines.append("")
lines.append("【不同同行人数的消费参考】")
for size in sorted(df['group_size'].unique()):
    sub = df[df['group_size'] == size]
    lines.append(f"- {int(size)}人同行：人均总消费{sub['total_cost'].mean():.0f}元，{len(sub)}条记录")

# ── 满意度分布 ──
lines.append("")
lines.append("【满意度分布】")
for s in sorted(df['satisfaction'].unique()):
    cnt = len(df[df['satisfaction'] == s])
    lines.append(f"- {int(s)}分：{cnt}人（{cnt/total*100:.1f}%）")

text = "\n".join(lines)
out_path.write_text(text, encoding="utf-8")
print(f"已写入 {out_path}")
print(f"文件大小: {len(text)} 字符")
print()
print(text)
