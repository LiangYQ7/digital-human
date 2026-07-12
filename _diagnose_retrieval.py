"""诊断：查看三个错题的实际检索结果"""
from brain.rag.retriever import retrieve
from brain.rag.store import get_collection

queries = [
    ("灵山大佛右手手印叫什么", "无畏印"),
    ("灵山大佛左手手印叫什么", "与愿印"),
    ("佛足坛的足印尺寸是多少", "1.2"),
]

for q, target in queries:
    print(f"\n{'='*60}")
    print(f"查询: {q}")
    print(f"目标词: {target}")
    print(f"{'='*60}")

    hits = retrieve(q, top_k=6)
    found_target = False
    for i, h in enumerate(hits):
        has_target = target in h["text"]
        marker = " ★★★ 目标在这里" if has_target else ""
        if has_target:
            found_target = True
        print(f"\n  [{i}] score={h['score']:.4f} | src={h['source'][:40]}{marker}")
        print(f"       {h['text'][:200]}...")

    if not found_target:
        print(f"\n  ❌ 前 6 条中未找到关键词 '{target}'！")

        # 全文搜索看是否存在
        coll = get_collection()
        all_data = coll.get()
        for doc, meta in zip(all_data["documents"], all_data["metadatas"]):
            if target in doc:
                print(f"\n  ✅ 知识库中存在: {meta.get('source','?')}")
                print(f"     内容片段: ...{doc[max(0, doc.index(target)-30):doc.index(target)+80]}...")
                break
        else:
            print(f"\n  ❌ 知识库中完全不存在关键词 '{target}'！")
