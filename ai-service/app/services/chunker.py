"""文本切片：把带页码的文字块合并成可入库的片段。

规则：
1. 按页切，永不跨页 —— 保证 page 准确
2. 页内按段落累积，单块不超过 700 字
3. 相邻块重叠 100 字
"""

TARGET_MAX = 700   # 单块正文上限（不含重叠）
OVERLAP = 100      # 相邻块重叠的字数

def build_chunks(blocks):
    """把文字块列表切成 chunk 列表。

    参数:
        blocks: extract_blocks() 返回的文字块列表

    返回:
        chunks: 每个元素包含 chunk_index / page / content / char_count
    """
    # 1. 按页分组，保持原顺序
    pages = {}
    for block in blocks:
        page_no = block["page"]
        if page_no not in pages:
            pages[page_no] = []
        pages[page_no].append(block)

    chunks = []
    chunk_index = 0

    for page_no in sorted(pages):
        # 2. 把这一页的所有块拼成一段长文本
        page_text = ""
        for block in pages[page_no]:
            if page_text != "":
                page_text += "\n\n"
            page_text += block["text"]

        # 3. 按段落累积成若干段
        page_texts = []
        buffer = ""
        for para in page_text.split("\n\n"):
            para = para.strip()
            if para == "":
                continue

            # 纯数字短块是页脚页码，丢掉
            if len(para) <= 4 and para.isdigit():
                continue

            # 单段超长：硬切
            while len(para) > TARGET_MAX:
                if buffer != "":
                    page_texts.append(buffer)
                    buffer = ""
                page_texts.append(para[:TARGET_MAX])
                para = para[TARGET_MAX:]

            if buffer == "":
                buffer = para
            elif len(buffer) + 2 + len(para) <= TARGET_MAX:
                buffer = buffer + "\n\n" + para
            else:
                page_texts.append(buffer)
                buffer = para

        if buffer != "":
            page_texts.append(buffer)

        # 4. 加重叠并编号
        previous_tail = ""
        for text in page_texts:
            if previous_tail == "":
                content = text
            else:
                content = previous_tail + "\n\n" + text

            chunks.append({
                "chunk_index": chunk_index,
                "page": page_no,
                "content": content,
                "char_count": len(content),
            })
            chunk_index = chunk_index + 1
            previous_tail = text[-OVERLAP:]

    return chunks
