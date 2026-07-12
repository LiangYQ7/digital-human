"""诊断 DashScope API 连接 — 排查 qwen-omni-turbo 调用方式"""
import os
from pathlib import Path

# 加载 .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import dashscope
from importlib.metadata import version as pkg_version

KEY = os.getenv("DASHSCOPE_API_KEY", "")
try:
    print(f"SDK 版本: {pkg_version('dashscope')}")
except Exception:
    print("SDK 版本: (无法获取)")
print(f"Key 前缀: {KEY[:15]}...")
print(f"Key 长度: {len(KEY)}")
print()

# 测试 1: MultiModalConversation（当前方式）
print("=" * 50)
print("测试 1: MultiModalConversation.call")
print("=" * 50)
dashscope.api_key = KEY
try:
    resp = dashscope.MultiModalConversation.call(
        model="qwen-omni-turbo",
        messages=[{"role": "user", "content": [{"type": "text", "text": "你好"}]}],
    )
    print(f"status_code={resp.status_code}")
    if resp.status_code == 200:
        print(f"SUCCESS: {resp.output.choices[0].message.content[0]['text'][:100]}")
    else:
        print(f"FAILED: code={resp.code}, message={resp.message}")
except Exception as e:
    print(f"EXCEPTION: {e}")

print()

# 测试 2: Generation.call（qwen-omni-turbo 推荐方式）
print("=" * 50)
print("测试 2: Generation.call")
print("=" * 50)
try:
    resp = dashscope.Generation.call(
        model="qwen-omni-turbo",
        messages=[{"role": "user", "content": [{"text": "你好"}]}],
    )
    print(f"status_code={resp.status_code}")
    if resp.status_code == 200:
        print(f"SUCCESS: {resp.output.choices[0].message.content[:100]}")
    else:
        print(f"FAILED: code={resp.code}, message={resp.message}")
except Exception as e:
    print(f"EXCEPTION: {e}")

print()

# 测试 3: 纯文本 Generation（qwen-turbo 作为对照）
print("=" * 50)
print("测试 3: Generation.call qwen-turbo (对照)")
print("=" * 50)
try:
    resp = dashscope.Generation.call(
        model="qwen-turbo",
        messages=[{"role": "user", "content": "你好"}],
    )
    print(f"status_code={resp.status_code}")
    if resp.status_code == 200:
        print(f"SUCCESS: {resp.output.choices[0].message.content[:100]}")
    else:
        print(f"FAILED: code={resp.code}, message={resp.message}")
except Exception as e:
    print(f"EXCEPTION: {e}")
