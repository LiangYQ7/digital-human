@echo off
echo ======================================== > "D:\Code\Vs code\digital_human\_explore_result.txt" 2>&1
echo 资料包探索报告 >> "D:\Code\Vs code\digital_human\_explore_result.txt" 2>&1
echo ======================================== >> "D:\Code\Vs code\digital_human\_explore_result.txt" 2>&1
echo. >> "D:\Code\Vs code\digital_human\_explore_result.txt" 2>&1

echo [1/3] 检查 Python 库... >> "D:\Code\Vs code\digital_human\_explore_result.txt" 2>&1
D:/conda_data/envs/fay/python.exe -c "import openpyxl; print('openpyxl OK'); import pandas; print('pandas OK'); import docx; print('docx OK')" >> "D:\Code\Vs code\digital_human\_explore_result.txt" 2>&1
echo. >> "D:\Code\Vs code\digital_human\_explore_result.txt" 2>&1

echo [2/3] 探索 Excel 文件... >> "D:\Code\Vs code\digital_human\_explore_result.txt" 2>&1
D:/conda_data/envs/fay/python.exe "D:\Code\Vs code\digital_human\explore_full.py" >> "D:\Code\Vs code\digital_human\_explore_result.txt" 2>&1
echo. >> "D:\Code\Vs code\digital_human\_explore_result.txt" 2>&1

echo [3/3] 完成 >> "D:\Code\Vs code\digital_human\_explore_result.txt" 2>&1
echo DONE > "D:\Code\Vs code\digital_human\_explore_done.txt"
