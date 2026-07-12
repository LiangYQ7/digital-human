import sys, os
sys.stdout = open(r'D:\Code\Vs code\digital_human\output.txt', 'w', encoding='utf-8')
sys.stderr = sys.stdout

print("Starting script...", flush=True)

import openpyxl
import pandas as pd

path = r'D:\20260323113204906\示范景区公开资料包\景点景区旅游数据行为分析数据.xlsx'

# 1. Sheet names
print("=== Sheet Names ===")
wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
sheets = list(wb.sheetnames)
for i, name in enumerate(sheets):
    print(f"  [{i}] {name}")
wb.close()
print(f"Total sheets: {len(sheets)}")

# 2. For each sheet, get first 5 rows + columns + total rows via pandas
for i, name in enumerate(sheets):
    print(f"\n{'='*60}")
    print(f"SHEET [{i}]: '{name}'")
    print(f"{'='*60}")
    try:
        df = pd.read_excel(path, sheet_name=name, nrows=None)
        total_rows = len(df)
        cols = list(df.columns)
        print(f"Total rows: {total_rows}")
        print(f"Columns ({len(cols)}): {cols}")
        print(f"\nFirst 5 rows:")
        print(df.head(5).to_string())
    except Exception as e:
        print(f"ERROR reading sheet '{name}': {e}")

# 3. Search for keywords
print(f"\n{'='*60}")
print("KEYWORD SEARCH: '灵山胜境' and '拈花湾'")
print(f"{'='*60}")

keywords = ['灵山胜境', '拈花湾']

for name in sheets:
    try:
        df = pd.read_excel(path, sheet_name=name, dtype=str)
        for kw in keywords:
            mask = df.apply(lambda row: row.astype(str).str.contains(kw, na=False).any(), axis=1)
            count = mask.sum()
            print(f"\nSheet '{name}' - '{kw}': {count} matching rows")
            if count > 0:
                sample = df[mask].head(3)
                print(f"  Sample (up to 3 rows):")
                print(sample.to_string())
    except Exception as e:
        print(f"ERROR searching sheet '{name}': {e}")

print("\nDONE.")
sys.stdout.close()
