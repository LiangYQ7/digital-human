"""LiveTalking 桥接器 测试。"""
from unittest.mock import MagicMock, patch

from brain.adapter.livetalking_bridge import send_text


@patch("brain.adapter.livetalking_bridge.requests.post")
def test_send_text_posts_with_tts(mock_post):
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"code": 0})
    ok = send_text("欢迎来到景区", sessionid="test123")
    assert ok is True
    args, kwargs = mock_post.call_args
    assert "human" in args[0]
    body = kwargs["json"]
    assert body["text"] == "欢迎来到景区"
    assert body["type"] == "echo"
    assert body["sessionid"] == "test123"
    assert "tts" in body
    assert "voice" in body["tts"]


@patch("brain.adapter.livetalking_bridge.requests.post")
def test_send_text_returns_false_on_error(mock_post):
    mock_post.return_value = MagicMock(status_code=500)
    assert send_text("x", sessionid="test") is False


@patch("brain.adapter.livetalking_bridge.requests.post")
def test_send_text_handles_network_error(mock_post):
    mock_post.side_effect = Exception("connection refused")
    assert send_text("x", sessionid="test") is False
