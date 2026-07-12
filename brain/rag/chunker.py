"""知识库分块器 —— 语义感知分块。

按自然段落/表格字段边界切分，关键事实独立成块，提高检索精确度。
"""
import hashlib
import re
from pathlib import Path

CHUNK_SIZE = 500
CHUNK_OVERLAP = 60


def _split_table_rows(text: str) -> list[str]:
    """只对结构化数据集（11 列超长行）做字段拆分。

    指南文档的简短表格（票务、演出时间等）保持整行，避免破坏上下文。
    """
    result: list[str] = []
    # 只匹配结构化数据集行：景区名 + 景点ID + 景点名
    structured = re.compile(
        r'^(灵山胜境|拈花湾禅意小镇)\s*\|\s*[A-Z]+-\d+\s*\|\s*([^|]+)\s*\|'
    )

    for line in text.split("\n"):
        line = line.strip()
        if not line or " | " not in line:
            continue

        m = structured.match(line)
        if not m:
            continue  # 不是结构化数据集行，保持原样交给段落分块

        # 结构化数据集：11 个字段，拆分关键字段为独立 chunk
        fields = [f.strip() for f in line.split("|")]
        if len(fields) >= 8:
            spot_name = fields[2]
            key_fields = {
                4: "建筑/景观参数",
                6: "文化内涵",
                7: "详细介绍",
            }
            for idx, label in key_fields.items():
                if idx < len(fields) and fields[idx]:
                    text_content = f"{spot_name} - {label}: {fields[idx]}"
                    if len(text_content) > 30:
                        result.append(text_content)

    return result


def _extract_guide_tables(text: str) -> list[str]:
    """提取指南文档 TABLE 块，按顺序配对景点标题。

    指南文档中景点标题和 TABLE 是分开的——
    标题先列完，TABLE 块统一放在后面，但顺序一一对应：
      灵山大佛：...\n灵山梵宫：...\n九龙灌浴：...\n
      --- TABLE 0 --- (灵山大佛)\n--- TABLE 1 --- (灵山梵宫)\n...
    """
    chunks: list[str] = []

    # 1. 提取景点标题（从"核心景点特色详解"之后）
    #    匹配形如 "景点名：副标题" 的标题行
    titles: list[str] = []
    in_section = False
    for line in text.split("\n"):
        line = line.strip()
        if "核心景点特色详解" in line:
            in_section = True
            continue
        if in_section:
            if line.startswith(("个性化游览", "实用游览", "其他特色")):
                break
            if "：" in line or ":" in line:
                name = line.split("：")[0].split(":")[0].strip()
                if 2 <= len(name) <= 20 and not name.startswith(("---", "项目", "票种")):
                    titles.append(name)

    # 2. 提取 TABLE 块，按编号配对
    table_pattern = re.compile(r'--- TABLE (\d+) ---\n(.*?)(?=\n--- TABLE \d+ ---|\n\n(?:[^-])|\Z)', re.DOTALL)
    for m in table_pattern.finditer(text):
        idx = int(m.group(1))
        body = m.group(2).strip()

        # 按 TABLE 内容确定上下文前缀（避免泛化的"灵山胜境"污染检索）
        if idx < len(titles):
            prefix = titles[idx]
        elif "票种" in body or "价格" in body:
            prefix = "灵山胜境门票"
        elif "素斋" in body or "住宿" in body or "餐饮" in body:
            prefix = "灵山胜境餐饮住宿"
        else:
            prefix = None  # 不加前缀，保留原始内容

        for line in body.split("\n"):
            line = line.strip()
            if not line or " | " not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2:
                field_name, field_value = parts[0], parts[1]
                if field_name in ("项目", "票种", "景区名称"):
                    continue
                if field_value and len(field_value) > 10:
                    if prefix:
                        chunks.append(f"{prefix} - {field_name}: {field_value}")
                    else:
                        chunks.append(f"{field_name}: {field_value}")

    return chunks


def _split_semantic(text: str) -> list[str]:
    """语义感知分块：表格字段 → 段落 → 句子 → 固定长度。"""
    chunks: list[str] = []

    # Step 0: 提取指南文档表格行并加上景点名上下文
    # "灵山梵宫：佛教艺术的卢浮宫\n--- TABLE 1 ---\n建筑规模 | 造价18亿"
    # → chunk: "灵山梵宫 - 建筑规模: 造价18亿"
    chunks.extend(_extract_guide_tables(text))

    # Step 0.5: 结构化数据集表格行拆字段（11 列超长行 → 独立事实块）
    table_chunks = _split_table_rows(text)
    chunks.extend(table_chunks)

    # Step 1: 全文按段落切（指南文档表格保留原样，不移除）
    paragraphs = re.split(r"\n\s*\n", text)

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # 结构化数据集的超长行已由 _split_table_rows 处理为字段 chunk，跳过原文避免重复
        if para.startswith(("灵山胜境 |", "拈花湾禅意小镇 |")):
            continue
        if len(para) <= CHUNK_SIZE:
            chunks.append(para)
        else:
            lines = para.split("\n")
            sub_chunks = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if len(line) <= CHUNK_SIZE:
                    sub_chunks.append(line)
                else:
                    sentences = re.split(r"(?<=[。！？])", line)
                    for sent in sentences:
                        sent = sent.strip()
                        if not sent:
                            continue
                        if len(sent) <= CHUNK_SIZE:
                            sub_chunks.append(sent)
                        else:
                            for i in range(0, len(sent), CHUNK_SIZE // 2):
                                piece = sent[i:i + CHUNK_SIZE].strip()
                                if piece:
                                    sub_chunks.append(piece)
            merged = []
            buf = ""
            for sc in sub_chunks:
                if not buf:
                    buf = sc
                elif len(buf) + len(sc) + 1 <= CHUNK_SIZE:
                    buf += "\n" + sc
                else:
                    merged.append(buf)
                    buf = sc
            if buf:
                merged.append(buf)
            chunks.extend(merged)

    # 重叠
    if CHUNK_OVERLAP > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-CHUNK_OVERLAP:]
            combined = prev_tail + "\n" + chunks[i]
            if len(combined) <= CHUNK_SIZE * 2:
                overlapped.append(combined)
            else:
                overlapped.append(chunks[i])
        chunks = overlapped

    return [c.strip() for c in chunks if c.strip()]


def chunk_documents(folder: Path) -> list[dict]:
    """把文件夹内所有 .txt 文件按语义分块。"""
    chunks: list[dict] = []
    for fp in sorted(folder.glob("**/*.txt")):
        text = fp.read_text(encoding="utf-8", errors="ignore")
        source = str(fp.relative_to(folder))
        for i, piece in enumerate(_split_semantic(text)):
            chunk_id = hashlib.md5(f"{fp}:{i}".encode()).hexdigest()
            chunks.append({
                "id": chunk_id,
                "text": piece,
                "source": source,
            })
    return chunks
