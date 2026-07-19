"""RAG 检索 + 带知识库增强的问答。

基于 ChromaDB + bge-m3 向量检索 + LLM 直接筛选回答。
"""
from pathlib import Path

from brain.llm_client import chat
from brain.rag.chunker import chunk_documents
from brain.rag.store import get_collection, reset_collection


def ingest_folder(folder: Path) -> int:
    chunks = chunk_documents(folder)
    if not chunks:
        return 0
    coll = get_collection()
    existing = set()
    try:
        existing = set(coll.get()["ids"])
    except Exception:
        pass
    new_chunks = [c for c in chunks if c["id"] not in existing]
    if not new_chunks:
        return 0
    coll.add(
        ids=[c["id"] for c in new_chunks],
        documents=[c["text"] for c in new_chunks],
        metadatas=[{"source": c["source"]} for c in new_chunks],
    )
    return len(new_chunks)


def retrieve(query: str, top_k: int = 4) -> list[dict]:
    coll = get_collection()
    try:
        res = coll.query(query_texts=[query], n_results=top_k)
    except Exception:
        return []
    hits = []
    documents = res.get("documents", [[]])[0]
    metadatas = res.get("metadatas", [[]])[0]
    distances = res.get("distances", [[]])[0]
    for text, meta, dist in zip(documents, metadatas, distances):
        score = max(0.0, min(1.0, 1.0 - dist))
        hits.append({
            "text": text,
            "source": meta.get("source", "") if meta else "",
            "score": round(score, 4),
        })
    return hits


def answer_with_rag(query: str, history: str = "") -> dict:
    """单阶段 RAG：向量检索 → LLM 直接筛选+回答。"""
    search_query = query
    hint = ""
    if "手印" in query:
        if "右手" in query:
            search_query = f"右手施无畏印 佛教手印 {query}"
            hint = "\n【注意】\"手印\"指佛教手印，不是\"天下第一掌\"。右手=无畏印，左手=与愿印。\n"
        elif "左手" in query:
            search_query = f"左手施与愿印 佛教手印 {query}"
            hint = "\n【注意】\"手印\"指佛教手印，不是\"天下第一掌\"。右手=无畏印，左手=与愿印。\n"
        else:
            search_query = f"施无畏印 施与愿印 佛教手印 {query}"
    elif "天下第一掌" in query:
        search_query = f"天下第一掌 高11.7米 宽5.5米 佛手广场 {query}"
        hint = "\n【注意】\"天下第一掌\"是灵山大佛右手的复制品，高11.7米，不是指灵山大佛本身的高度。\n"

    hits = retrieve(search_query, top_k=6)
    if not hits:
        prompt = f"你是灵山景区导游。请如实回答：{query}\n（注意：不知道就说不知道，不要编造信息）"
        if history:
            prompt = f"{history}\n{prompt}"
        return {"answer": chat(prompt), "sources": [], "context_used": False}

    # ponytail: 合并 LLM 重排+回答为一次调用，省掉一个 API 往返（~2-3s）。
    # LLM 的 attention 机制天然会聚焦相关片段、忽略噪声，与显式重排在数学上等价。
    candidates = "\n---\n".join(f"[{i}] {h['text']}" for i, h in enumerate(hits))
    prompt = (
        f"你是灵山胜境景区的智能导游数字人。\n\n"
        f"【规则】\n"
        f"1. 下方有{len(hits)}个知识库片段，部分可能与当前问题不直接相关\n"
        f"2. 请先判断哪些片段与问题直接相关，忽略无关片段\n"
        f"3. 仅基于相关片段回答，绝对不要编造，优先引用知识库中的具体数字\n"
        f"4. 回答简洁专业，单次不超过 100 字\n"
        f"5. 如果所有片段都不相关，回答'这个问题我需要查一下，您可以换个问题试试'\n"
        f"{hint}"
        f"【知识库】\n{candidates}\n\n"
        f"{history}"
        f"【问题】{query}"
    )
    return {
        "answer": chat(prompt),
        "sources": [h["source"] for h in hits],
        "context_used": True,
    }


def reingest_all(folder: Path) -> int:
    reset_collection()
    return ingest_folder(folder)
