@echo off
python --version > "D:\Code\Vs code\digital_human\_out1.txt" 2>&1
D:/conda_data/envs/fay/python.exe --version > "D:\Code\Vs code\digital_human\_out2.txt" 2>&1
D:/conda_data/envs/fay/python.exe -c "import docx; print('docx ok')" > "D:\Code\Vs code\digital_human\_out3.txt" 2>&1
echo DONE > "D:\Code\Vs code\digital_human\_done.txt"
