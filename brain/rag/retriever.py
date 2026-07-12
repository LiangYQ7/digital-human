"""RAG 检索 + 带知识库增强的问答。

基于 ChromaDB + bge-m3 向量检索 + LLM 重排序。
"""
import re
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
    """两阶段 RAG：向量粗筛 → LLM 精选 → 回答。"""
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

    # ── Stage 1 ──
    hits = retrieve(search_query, top_k=12)
    if not hits:
        prompt = f"你是灵山景区导游。请如实回答：{query}\n（注意：不知道就说不知道，不要编造信息）"
        if history:
            prompt = f"{history}\n{prompt}"
        return {"answer": chat(prompt), "sources": [], "context_used": False}

    # ── Stage 2: LLM 重排序 ──
    candidates = "\n---\n".join(f"[{i}] {h['text']}" for i, h in enumerate(hits))
    rerank_prompt = (
        f"以下是关于灵山胜境的多个知识片段，编号 0-{len(hits)-1}。\n"
        f"问题：{query}\n\n"
        f"请选出与问题最直接相关的 3-4 个片段（只输出编号，如\"0,3,5,7\"），不要输出其他内容。\n\n"
        f"{candidates}"
    )
    selected = chat(rerank_prompt)
    selected_ids = [int(s) for s in re.findall(r'\d+', selected) if s.isdigit() and 0 <= int(s) < len(hits)]
    if len(selected_ids) < 3:
        for i in range(len(hits)):
            if i not in selected_ids:
                selected_ids.append(i)
            if len(selected_ids) >= 4:
                break
    if not selected_ids:
        selected_ids = list(range(min(4, len(hits))))

    filtered = [hits[i] for i in selected_ids]
    context = "\n---\n".join(f"[来源：{h['source']}] {h['text']}" for h in filtered)

    # ── Stage 3 ──
    prompt = (
        f"你是灵山胜境景区的智能导游数字人。\n\n"
        f"【规则】\n"
        f"1. 仅根据下方知识库内容回答，绝对不要编造\n"
        f"2. 优先引用知识库中的具体数字\n"
        f"3. 回答简洁专业，单次不超过 100 字\n"
        f"4. 如果知识库中确实没有相关信息，回答'这个问题我需要查一下，您可以换个问题试试'\n"
        f"{hint}"
        f"【知识库】\n{context}\n\n"
        f"{history}"
        f"【问题】{query}"
    )
    return {
        "answer": chat(prompt),
        "sources": [h["source"] for h in filtered],
        "context_used": True,
    }


def reingest_all(folder: Path) -> int:
    reset_collection()
    return ingest_folder(folder)
