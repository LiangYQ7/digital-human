import os, sys
# Write to multiple locations to find where it lands
paths = [
    r'D:\Code\Vs code\digital_human\_p1.txt',
    r'D:\_p2.txt',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '_p3.txt') if '__file__' in dir() else 'skip',
]
with open(r'D:\Code\Vs code\digital_human\_p1.txt', 'w') as f:
    f.write(f'cwd={os.getcwd()}\npython={sys.executable}\n')
print("DONE")
