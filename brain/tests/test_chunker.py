from pathlib import Path

from brain.rag.chunker import chunk_documents


def test_chunk_documents_splits_long_text(tmp_path):
    f = tmp_path / "scenic.txt"
    f.write_text("A" * 600 + "\n\n" + "B" * 600, encoding="utf-8")
    chunks = chunk_documents(tmp_path)
    assert len(chunks) >= 2
    assert all("text" in c and "source" in c and "id" in c for c in chunks)
    assert all(len(c["text"]) <= 400 for c in chunks)


def test_chunk_documents_handles_empty_folder(tmp_path):
    chunks = chunk_documents(tmp_path)
    assert chunks == []


def test_chunk_documents_handles_multiple_files(tmp_path):
    (tmp_path / "a.txt").write_text("Hello " * 100, encoding="utf-8")
    (tmp_path / "b.txt").write_text("World " * 100, encoding="utf-8")
    chunks = chunk_documents(tmp_path)
    assert len(chunks) >= 2
    sources = {c["source"] for c in chunks}
    assert "a.txt" in sources
    assert "b.txt" in sources
