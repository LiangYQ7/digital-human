from unittest.mock import patch

from brain.pipeline import handle_user_input


@patch("brain.pipeline.send_text", return_value=True)
@patch("brain.pipeline.chat", return_value="您好！景区9点开门。")
def test_pipeline_full_chain(mock_chat, mock_send):
    result = handle_user_input("几点开门")
    assert result["reply"] == "您好！景区9点开门。"
    assert mock_send.called
    assert result["latency_sec"] >= 0
    assert result["delivered"] is True
