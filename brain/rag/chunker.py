import hashlib
from pathlib import Path

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80


def _split_text(text: str) -> list[str]:
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        pieces.append(text[start:end])
        if end == len(text):
            break
        start = end - CHUNK_OVERLAP
    return [p for p in (s.strip() for s in pieces) if p]


def chunk_documents(folder: Path) -> list[dict]:
    """把文件夹内所有 .txt 文件按 chunk_size 分块。

    Returns:
        list[dict]: 每项含 id / text / source
    """
    chunks: list[dict] = []
    for fp in sorted(folder.glob("**/*.txt")):
        text = fp.read_text(encoding="utf-8", errors="ignore")
        for i, piece in enumerate(_split_text(text)):
            chunks.append({
                "id": hashlib.md5(f"{fp}:{i}".encode()).hexdigest(),
                "text": piece,
                "source": str(fp.relative_to(folder)),
            })
    return chunks
