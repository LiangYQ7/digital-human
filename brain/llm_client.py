import os
import yaml
from pathlib import Path

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


def chat(user_text: str, image_path: str | None = None) -> str:
    """调用多模态 LLM。image_path 非空时走多模态通路。

    Args:
        user_text: 用户输入文本
        image_path: 可选图片路径，非空时以 base64 data URL 传入

    Returns:
        LLM 返回的文本回复

    Raises:
        ValueError: 配置或 API 调用出错时
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
    if image_path:
        mime = mimetypes.guess_type(image_path)[0] or "image/png"
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
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
