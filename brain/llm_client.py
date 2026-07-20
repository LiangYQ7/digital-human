import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# 自动加载项目根目录的 .env 文件（作为环境变量兜底）
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=True)  # override=True: .env 文件中的值优先于系统环境变量

_CONFIG = None
_SYSTEM_PROMPT = None


def _config():
    global _CONFIG
    if _CONFIG is None:
        cfg_path = Path(__file__).parent / "config" / "settings.yaml"
        _CONFIG = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    return _CONFIG


def _system_prompt():
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        p = Path(__file__).parent / "config" / "prompts" / "system.txt"
        _SYSTEM_PROMPT = p.read_text(encoding="utf-8")
    return _SYSTEM_PROMPT


def chat(user_text: str, image_path: str | None = None, image_base64: str | None = None) -> str:
    """调用多模态 LLM。传入图片时走多模态通路。

    Args:
        user_text: 用户输入文本
        image_path: 可选本地图片路径，非空时以 base64 data URL 传入
        image_base64: 可选 Base64 编码图片数据（优先于 image_path）

    Returns:
        LLM 返回的文本回复
    """
    import base64
    import mimetypes

    import dashscope

    cfg = _config()["llm"]
    api_key = os.getenv(cfg["api_key_env"])
    if not api_key:
        raise ValueError(f"环境变量 {cfg['api_key_env']} 未设置")

    dashscope.api_key = api_key

    content = [{"type": "text", "text": user_text}]

    # 组装图片：优先使用 base64（来自浏览器上传），其次本地路径
    if image_base64:
        # 检测 data URL 前缀
        if image_base64.startswith("data:"):
            b64 = image_base64.split(",", 1)[-1] if "," in image_base64 else image_base64
            mime = image_base64.split(";")[0].replace("data:", "")
        else:
            b64 = image_base64
            mime = "image/jpeg"
        content.append({
            "type": "image",
            "image": f"data:{mime};base64,{b64}",
        })
    elif image_path:
        mime = mimetypes.guess_type(image_path)[0] or "image/png"
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        content.append({
            "type": "image",
            "image": f"data:{mime};base64,{b64}",
        })

    messages = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": content},
    ]
    resp = dashscope.MultiModalConversation.call(
        model=cfg["model"], messages=messages
    )
    try:
        return resp.output.choices[0].message.content[0]["text"]
    except (AttributeError, IndexError, KeyError) as e:
        raise ValueError(f"LLM 返回格式异常: {e}，原始响应: {resp}")
