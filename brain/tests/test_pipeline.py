"""核心流水线 测试。"""
from unittest.mock import patch

from brain.pipeline import handle_user_input, _is_route_intent, _is_rag_intent


class TestIntentDetection:
    def test_route_keywords(self):
        assert _is_route_intent("帮我推荐一条路线") is True
        assert _is_route_intent("怎么逛比较好") is True
        assert _is_route_intent("一日游怎么安排") is True
        assert _is_route_intent("历史游览路线推荐") is True

    def test_not_route_for_consumption(self):
        """消费规划不应触发路线。"""
        assert _is_route_intent("帮我规划一个消费预算") is False
        assert _is_route_intent("帮我推荐门票信息") is False

    def test_rag_keywords(self):
        assert _is_rag_intent("灵山大佛的历史") is True
        assert _is_rag_intent("门票多少钱") is True
        assert _is_rag_intent("消费预算怎么规划") is True

    def test_neutral_falls_to_chat(self):
        assert _is_route_intent("你好") is False
        assert _is_rag_intent("你好") is False


class TestPipeline:
    @patch("brain.pipeline.send_text", return_value=True)
    @patch("brain.pipeline.chat", return_value="您好！我是灵山景区的智能导游。")
    def test_chat_intent(self, mock_chat, mock_send):
        result = handle_user_input("你好", sessionid="test")
        assert result["reply"] == "您好！我是灵山景区的智能导游。"
        assert result["intent"] == "chat"
        assert result["delivered"] is True
        mock_chat.assert_called_once()
        mock_send.assert_called_once_with("您好！我是灵山景区的智能导游。", "test")

    @patch("brain.pipeline.send_text", return_value=True)
    @patch("brain.pipeline._handle_rag", return_value="灵山大佛高88米。")
    def test_rag_intent(self, mock_rag, mock_send):
        result = handle_user_input("灵山大佛有多高", sessionid="test")
        assert result["intent"] == "rag"
        assert result["delivered"] is True
        mock_rag.assert_called_once_with("灵山大佛有多高", history="")

    @patch("brain.pipeline.send_text", return_value=True)
    @patch("brain.pipeline._handle_route")
    def test_route_intent(self, mock_route, mock_send):
        mock_route.return_value = "为您规划了4小时路线：灵山大佛 → 梵宫"
        result = handle_user_input("帮我推荐一条游览路线", sessionid="test")
        assert result["intent"] == "route"
        assert result["delivered"] is True
        mock_route.assert_called_once()

    @patch("brain.pipeline.send_text", return_value=True)
    @patch("brain.pipeline.chat", return_value="好的。")
    def test_latency_non_negative(self, mock_chat, mock_send):
        result = handle_user_input("今天天气如何", sessionid="test")
        assert result["latency_sec"] >= 0

    @patch("brain.pipeline.send_text", return_value=False)
    @patch("brain.pipeline.chat", return_value="回答。")
    def test_delivery_failure_reported(self, mock_chat, mock_send):
        result = handle_user_input("你好", sessionid="test")
        assert result["delivered"] is False
