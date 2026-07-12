import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# 自动加载项目根目录的 .env 文件
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


@pytest.fixture
def api_key():
    k = os.getenv("DASHSCOPE_API_KEY")
    if not k:
        pytest.skip("DASHSCOPE_API_KEY 未设置")
    return k
