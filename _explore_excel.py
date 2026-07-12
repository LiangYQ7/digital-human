"""从灵山.xlsx提取游客消费统计摘要，写入 brain/data/raw 供 RAG 入库"""
import json
from pathlib import Path
import pandas as pd

xlsx_path = Path(r"D:\20260323113204906\示范景区公开资料包\灵山.xlsx")
out_path = Path(r"D:\Code\Vs code\digital_human\brain\data\raw\灵山游客消费统计.txt")

df = pd.read_excel(xlsx_path)
print(f"行数: {len(df)}")
print(f"列名: {list(df.columns)}")
print()
print(df.head(3).to_string())
print()
print(df.describe().to_string())
