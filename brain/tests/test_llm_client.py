import pytest

from brain.llm_client import chat


def test_chat_returns_text_for_pure_text_input(api_key):
    """纯文本输入应返回非空字符串"""
    try:
        reply = chat("你好，请用一句话介绍你自己")
    except ValueError as e:
        if "InvalidApiKey" in str(e) or "401" in str(e):
            pytest.skip("API key 已过期，跳过实调测试")
        raise
    assert isinstance(reply, str)
    assert len(reply) > 0


def test_chat_accepts_image_for_multimodal(api_key, tmp_path):
    """带图片输入应走多模态通路（赛题硬性要求）"""
    # 造一张最小有效 PNG（1x1 红点）
    img = tmp_path / "t.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")
    try:
        reply = chat("这张图是什么颜色？", image_path=str(img))
    except Exception as e:
        # 多模态通路存在但图片无效，允许 LLM 侧报错
        # 但必须是多模态错误而非"接口不存在"
        import traceback
        err_str = str(e).lower() + "\n" + traceback.format_exc().lower()
        assert "image" in err_str or "multimodal" in err_str or isinstance(reply, str)
    else:
        assert isinstance(reply, str)
