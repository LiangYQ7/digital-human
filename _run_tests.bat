@echo off
cd /d "D:\Code\Vs code\digital_human"
echo === Step 1: Verify Python Environment === > "_test_results.txt" 2>&1
D:\conda_data\envs\fay\python.exe -c "import sys; print(sys.executable); print('OK')" >> "_test_results.txt" 2>&1
echo. >> "_test_results.txt" 2>&1
echo === Step 2: Run Brain Tests === >> "_test_results.txt" 2>&1
D:\conda_data\envs\fay\python.exe -m pytest brain/tests/ -v --tb=short >> "_test_results.txt" 2>&1
echo. >> "_test_results.txt" 2>&1
echo DONE >> "_test_results.txt" 2>&1
