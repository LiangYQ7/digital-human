"""RAG 检索 + 问答 测试。"""
from unittest.mock import patch, MagicMock

from brain.rag.retriever import retrieve, answer_with_rag, ingest_folder


class TestRetrieve:
    """检索接口测试。"""

    @patch("brain.rag.retriever.get_collection")
    def test_retrieve_returns_ranked_hits(self, mock_coll):
        mock_coll.return_value.query.return_value = {
            "documents": [["灵山大佛高88米，是世界最大的露天青铜佛像。"]],
            "metadatas": [[{"source": "guide.txt"}]],
            "distances": [[0.1]],
        }
        hits = retrieve("灵山大佛有多高", top_k=3)
        assert isinstance(hits, list)
        assert len(hits) == 1
        assert "text" in hits[0] and "source" in hits[0] and "score" in hits[0]
        assert hits[0]["source"] == "guide.txt"
        assert hits[0]["score"] >= 0.8  # 1 - 0.1 = 0.9

    @patch("brain.rag.retriever.get_collection")
    def test_retrieve_empty_on_error(self, mock_coll):
        mock_coll.return_value.query.side_effect = RuntimeError("db down")
        hits = retrieve("test", top_k=3)
        assert hits == []


class TestAnswerWithRAG:
    """RAG 问答测试。"""

    @patch("brain.rag.retriever.chat")
    @patch("brain.rag.retriever.get_collection")
    def test_answer_with_rag_injects_context(self, mock_coll, mock_chat):
        mock_coll.return_value.query.return_value = {
            "documents": [["灵山胜境位于无锡太湖之滨。开放时间8:00-17:00。"]],
            "metadatas": [[{"source": "intro.txt"}]],
            "distances": [[0.05]],
        }
        mock_chat.return_value = "灵山胜境开放时间为每天8:00到17:00。"

        result = answer_with_rag("景区几点开门")

        assert result["answer"] == "灵山胜境开放时间为每天8:00到17:00。"
        assert result["sources"] == ["intro.txt"]
        assert result["context_used"] is True
        # 验证 LLM 收到了知识库上下文
        call_text = mock_chat.call_args[0][0]
        assert "灵山胜境位于无锡太湖之滨" in call_text
        assert "开放时间" in call_text

    @patch("brain.rag.retriever.chat")
    @patch("brain.rag.retriever.get_collection")
    def test_answer_with_rag_no_hits_fallback_to_pure_llm(self, mock_coll, mock_chat):
        mock_coll.return_value.query.return_value = {
            "documents": [[]], "metadatas": [[]], "distances": [[]]
        }
        mock_chat.return_value = "这个问题我暂时无法回答。"

        result = answer_with_rag("火星上有景区吗")

        assert result["context_used"] is False
        assert result["sources"] == []


class TestIngestFolder:
    """知识库入库测试。"""

    @patch("brain.rag.retriever.get_collection")
    def test_ingest_folder_adds_chunks(self, mock_coll, tmp_path):
        mock_coll.return_value.get.return_value = {"ids": []}
        mock_coll.return_value.add.return_value = None

        f = tmp_path / "test.txt"
        f.write_text("A" * 600 + "\n\n" + "B" * 600, encoding="utf-8")

        count = ingest_folder(tmp_path)
        assert count >= 2
        mock_coll.return_value.add.assert_called_once()

    @patch("brain.rag.retriever.get_collection")
    def test_ingest_empty_folder_returns_zero(self, mock_coll, tmp_path):
        count = ingest_folder(tmp_path)
        assert count == 0
