"""Test that explores the Excel file and writes results to a text file."""
import sys
import os

OUTPUT_PATH = r"D:\Code\Vs code\digital_human\_excel_report.txt"

def write_report(text):
    with open(OUTPUT_PATH, 'a', encoding='utf-8') as f:
        f.write(text + '\n')

def test_explore_excel():
    """Explore the Excel file: sheets, columns, row counts, keyword search."""
    import openpyxl
    import pandas as pd
    
    path = r'D:\20260323113204906\示范景区公开资料包\景点景区旅游数据行为分析数据.xlsx'
    
    write_report("=" * 70)
    write_report("EXCEL EXPLORATION REPORT")
    write_report("=" * 70)
    
    # 1. Sheet names via openpyxl
    write_report("\n>>> 1. SHEET NAMES (openpyxl)")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheets = list(wb.sheetnames)
    for i, name in enumerate(sheets):
        write_report(f"  Sheet [{i}]: '{name}'")
    wb.close()
    write_report(f"Total sheets: {len(sheets)}")
    
    # 2. Per-sheet exploration
    for i, name in enumerate(sheets):
        write_report(f"\n{'='*60}")
        write_report(f">>> 2.{i} SHEET: '{name}'")
        write_report(f"{'='*60}")
        try:
            df = pd.read_excel(path, sheet_name=name, nrows=None)
            total_rows = len(df)
            cols = list(df.columns)
            write_report(f"Total rows: {total_rows}")
            write_report(f"Columns ({len(cols)}):")
            for c in cols:
                write_report(f"  - {c}")
            write_report(f"\nFirst 5 rows:")
            write_report(df.head(5).to_string())
            write_report(f"\nLast 2 rows:")
            write_report(df.tail(2).to_string())
        except Exception as e:
            write_report(f"ERROR: {e}")
    
    # 3. Keyword search
    write_report(f"\n{'='*60}")
    write_report(">>> 3. KEYWORD SEARCH: '灵山胜境' & '拈花湾'")
    write_report(f"{'='*60}")
    
    keywords = ['灵山胜境', '拈花湾']
    
    for name in sheets:
        try:
            df = pd.read_excel(path, sheet_name=name, dtype=str)
            write_report(f"\n--- Sheet '{name}' ---")
            for kw in keywords:
                mask = df.apply(lambda row: row.astype(str).str.contains(kw, na=False).any(), axis=1)
                count = mask.sum()
                write_report(f"  '{kw}': {count} matching rows")
                if count > 0:
                    sample = df[mask].head(5)
                    write_report(f"  Sample (up to 5 rows):")
                    write_report(sample.to_string())
        except Exception as e:
            write_report(f"  ERROR: {e}")
    
    write_report("\n" + "=" * 70)
    write_report("REPORT COMPLETE")
    write_report("=" * 70)
    
    assert True  # Always pass
