"""景区知识库问答准确率评测。

从 JSONL 测试集逐条调用 RAG 问答，按关键词命中率计算准确率。
赛题要求准确率 ≥ 90%（红线）。
"""
import json
import time
from pathlib import Path

from brain.rag.retriever import answer_with_rag


def _hit_keywords(answer: str, keywords: list[str]) -> bool:
    """检查 answer 是否包含至少一个指定关键词（OR 逻辑，不区分大小写）。

    采用 OR 而非 AND——评测关注事实正确性，而非措辞一致。
    设计关键词时：一个必须出现的核心词即可，多个可选词提高容错。
    """
    a = answer.lower()
    return any(k.lower() in a for k in keywords)


def run(testset_path: Path) -> dict:
    """运行评测。

    Args:
        testset_path: JSONL 文件，每行 {"q": str, "a_keywords": [str, ...]}

    Returns:
        {
            "total": 题目总数,
            "correct": 答对数,
            "accuracy": 准确率 (0~1),
            "duration_sec": 总耗时,
            "details": [{q, answer, expected_keywords, hit, sources}, ...]
        }
    """
    details: list[dict] = []
    t0 = time.time()

    with open(testset_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            item = json.loads(line)
            res = answer_with_rag(item["q"])
            hit = _hit_keywords(res["answer"], item.get("a_keywords", []))
            details.append({
                "q": item["q"],
                "answer": res["answer"],
                "expected_keywords": item.get("a_keywords", []),
                "hit": hit,
                "sources": res.get("sources", []),
            })
            # 限速：每题 2 次 LLM 调用，间隔 3 秒避免触发免费层 QPM
            time.sleep(3)

    total = len(details)
    correct = sum(1 for d in details if d["hit"])
    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total, 3) if total else 0.0,
        "duration_sec": round(time.time() - t0, 1),
        "details": details,
    }


def _print_report(report: dict) -> None:
    """打印人类可读的评测报告。"""
    print(f"\n{'='*60}")
    print(f"  准确率评测报告")
    print(f"{'='*60}")
    print(f"  总题数: {report['total']}")
    print(f"  正确:   {report['correct']}")
    print(f"  准确率: {report['accuracy']*100:.1f}%")
    print(f"  耗时:   {report['duration_sec']:.1f}s")

    passed = "✅ 达标" if report["accuracy"] >= 0.90 else "❌ 未达标（需 ≥ 90%）"
    print(f"  判定:   {passed}")
    print(f"{'='*60}")

    # 打印错题
    failed = [d for d in report["details"] if not d["hit"]]
    if failed:
        print(f"\n错题详情（{len(failed)} 题）：")
        for i, d in enumerate(failed, 1):
            print(f"\n--- 错题 {i} ---")
            print(f"  问题: {d['q']}")
            print(f"  期望关键词: {d['expected_keywords']}")
            print(f"  实际回答: {d['answer'][:200]}")
            print(f"  引用来源: {d['sources']}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m brain.rag.evaluate <testset.jsonl>")
        sys.exit(1)
    report = run(Path(sys.argv[1]))
    _print_report(report)
