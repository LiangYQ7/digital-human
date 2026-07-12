"""准确率评测 测试。"""
import json
from unittest.mock import patch

from brain.rag.evaluate import run, _hit_keywords


class TestHitKeywords:
    def test_all_keywords_present(self):
        assert _hit_keywords("灵山大佛高88米，位于无锡", ["灵山", "88米"]) is True

    def test_missing_keyword(self):
        assert _hit_keywords("灵山大佛很高", ["88米"]) is False

    def test_case_insensitive(self):
        assert _hit_keywords("LINGSHAN大佛", ["lingshan"]) is True

    def test_empty_keywords_always_hit(self):
        assert _hit_keywords("随便什么回答", []) is True


class TestRun:
    def test_run_with_mocked_rag(self, tmp_path):
        ts = tmp_path / "qa.jsonl"
        ts.write_text(
            json.dumps({
                "q": "灵山大佛有多高",
                "a_keywords": ["88米", "青铜"],
            }, ensure_ascii=False) + "\n" +
            json.dumps({
                "q": "梵宫有什么特色",
                "a_keywords": ["壁画", "琉璃"],
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        with patch("brain.rag.evaluate.answer_with_rag") as mock_rag:
            # 第一题命中，第二题不命中
            mock_rag.side_effect = [
                {"answer": "灵山大佛高88米，是世界最大的露天青铜佛像", "sources": ["a.txt"]},
                {"answer": "梵宫以木雕和穹顶闻名", "sources": ["b.txt"]},
            ]
            report = run(ts)

        assert report["total"] == 2
        assert report["correct"] == 1
        assert report["accuracy"] == 0.5
        assert report["details"][0]["hit"] is True
        assert report["details"][1]["hit"] is False

    def test_run_handles_empty_file(self, tmp_path):
        ts = tmp_path / "empty.jsonl"
        ts.write_text("", encoding="utf-8")
        with patch("brain.rag.evaluate.answer_with_rag"):
            report = run(ts)
        assert report["total"] == 0
        assert report["accuracy"] == 0.0

    def test_run_skips_comments(self, tmp_path):
        ts = tmp_path / "qa.jsonl"
        ts.write_text(
            "# 这是一条注释\n" +
            json.dumps({"q": "test", "a_keywords": ["x"]}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        with patch("brain.rag.evaluate.answer_with_rag") as mock_rag:
            mock_rag.return_value = {"answer": "x", "sources": []}
            report = run(ts)
        assert report["total"] == 1
