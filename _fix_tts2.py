"""Fix TTS page: repair broken Chinese and simplify transcribeAudio"""
p = r'D:/Code/Vs code/digital_human/third_party/LiveTalking/web/tts/index.html'
with open(p, 'rb') as f:
    raw = f.read()

# Replace broken UTF-8 sequences with proper Chinese
raw = raw.replace('����ѡ����Ƶ�ļ�'.encode('gbk', errors='replace'), '请先选择音频文件'.encode('utf-8'))
raw = raw.replace('����ʶ������...'.encode('gbk', errors='replace'), '正在识别语音...'.encode('utf-8'))

# Decode properly
c = raw.decode('utf-8', errors='replace')

# Find the script block and check all function definitions for garbled text
import re
# Replace any remaining garbled patterns
c = c.replace('\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd', '请先选择音频文件')
c = c.replace('\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd', '正在识别语音...')
c = c.replace('\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd', '识别完成')
c = c.replace('\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd', '未识别到语音内容')
c = c.replace('\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd', '识别失败: ')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)

print('Fixed. Verifying...')

# Verify
with open(p, 'r', encoding='utf-8') as f:
    v = f.read()
idx = v.find('async function transcribeAudio')
sample = v[idx:idx+500]
if '请先' in sample and '正在识别' in sample:
    print('Chinese OK')
else:
    print('STILL BROKEN:', repr(sample[:200]))
