import openpyxl
import pandas as pd

print("=== Libraries available ===")
print("openpyxl: OK")
print("pandas: OK")

print("\n=== Sheet names ===")
wb = openpyxl.load_workbook(r'D:\20260323113204906\示范景区公开资料包\景点景区旅游数据行为分析数据.xlsx', read_only=True)
for i, s in enumerate(wb.sheetnames):
    print(f"  Sheet {i}: [{s}]")
wb.close()
