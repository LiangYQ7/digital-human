import os
import pytest


@pytest.fixture
def api_key():
    k = os.getenv("DASHSCOPE_API_KEY")
    if not k:
        pytest.skip("DASHSCOPE_API_KEY 未设置")
    return k
