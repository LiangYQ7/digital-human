"""找出 DashScope ASR 的正确调用方式"""
import os, requests
from dotenv import load_dotenv
load_dotenv(r"D:\Code\Vs code\digital_human\.env")

KEY = os.getenv("DASHSCOPE_API_KEY", "")

# 方法1：HTTP 直调 paraformer-v1
print("=== 方法1: HTTP paraformer-v1 ===")
try:
    r = requests.post(
        "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription",
        headers={"Authorization": f"Bearer {KEY}"},
        files={"file": ("test.wav", b"", "audio/wav")},
        data={"model": "paraformer-v1"},
        timeout=10,
    )
    print(r.status_code, r.text[:200])
except Exception as e:
    print(f"FAIL: {e}")

# 方法2：dashscope MultiModalConversation 的 audio 能力
print("\n=== 方法2: qwen-omni 音频识别 ===")
try:
    import dashscope
    dashscope.api_key = KEY
    resp = dashscope.MultiModalConversation.call(
        model="qwen-omni-turbo",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "请转写这段音频内容"},
            {"audio": "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav"}
        ]}],
    )
    print(resp.status_code, str(resp)[:200])
except Exception as e:
    print(f"FAIL: {e}")
