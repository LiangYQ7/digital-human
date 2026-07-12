"""检查 .env 换行符格式 + 验证 API key 加载"""
from pathlib import Path
from dotenv import load_dotenv
import os

env = Path(r"D:\Code\Vs code\digital_human\.env")
raw = env.read_bytes()

has_crlf = b"\r\n" in raw
print(f"CRLF 换行符: {'存在' if has_crlf else '不存在 (LF only)'}")
print(f"文件大小: {len(raw)} bytes")

# 加载并检查 key
os.environ.pop("DASHSCOPE_API_KEY", None)  # 清除现有
load_dotenv(env)
key = os.getenv("DASHSCOPE_API_KEY", "")
print(f"加载后 key 长度: {len(key)}")
print(f"key 含 \\r: {chr(13) in key}")
print(f"key 前缀: {key[:20]}...")
print(f"key 后缀: ...{key[-10:]}")
print()

# 验证 key 不含特殊字符
for i, ch in enumerate(key):
    if ord(ch) < 32:
        print(f"⚠ 位置 {i}: 控制字符 ASCII={ord(ch)}")
        break
else:
    print("✅ key 不含控制字符")
