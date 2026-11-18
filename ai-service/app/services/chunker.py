"""文本切片：把带页码和坐标的文字块合并成可入库的片段。

规则：
1. 按页切，永不跨页 —— 保证 page 准确
2. 页内按段落累积，单块不超过 700 字
3. 相邻块重叠 100 字
4. 每个 chunk 记录来源块的 bbox 并集，并标记 bbox_mode（#40）

说明：
- 本文件只负责“产出坐标”，不负责落库；落库在 db/chunks.py。
- 切片文本必须与 #18 的旧实现逐字节一致，改这里要跑 check_bbox.py 的基线哈希。
"""

TARGET_MAX = 700   # 单块正文上限（不含重叠）
OVERLAP = 100      # 相邻块重叠的字数

# 双栏判定参数
COLUMN_MIN_BLOCKS = 3          # 左右栏各至少 3 个有效文本块
COLUMN_MIN_BLOCK_CHARS = 30    # 太短的块（页码、公式碎片）不参与判定
COLUMN_MIN_BLOCK_WIDTH = 0.15  # 排除侧边水印/页码等窄块
COLUMN_MIN_SPAN = 0.5          # 两栏合起来至少跨页高 50%
DOC_DOUBLE_COLUMN_RATIO = 0.5  # 双栏页占正文页一半以上，判整篇双栏


def _block_bbox(block):
    """取 block 的归一化 bbox；字段缺失或非法时返回 None。"""
    x0 = block.get("bbox_x0")
    y0 = block.get("bbox_y0")
    x1 = block.get("bbox_x1")
    y1 = block.get("bbox_y1")
    if x0 is None or y0 is None or x1 is None or y1 is None:
        return None
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        return None
    return (x0, y0, x1, y1)


def _union_bbox(bboxes):
    """把多个 bbox 合成一个并集；无效时返回 None。"""
    valid = [bbox for bbox in bboxes if bbox is not None]
    if not valid:
        return None

    x0 = min(bbox[0] for bbox in valid)
    y0 = min(bbox[1] for bbox in valid)
    x1 = max(bbox[2] for bbox in valid)
    y1 = max(bbox[3] for bbox in valid)

    x0 = round(min(max(x0, 0.0), 1.0), 6)
    y0 = round(min(max(y0, 0.0), 1.0), 6)
    x1 = round(min(max(x1, 0.0), 1.0), 6)
    y1 = round(min(max(y1, 0.0), 1.0), 6)

    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1, y1)


def _tail_pieces(pieces, size):
    """取一个 chunk 末尾 size 个字符覆盖到的来源段。

    重叠文本是上一 chunk 的尾巴；引用 bbox 必须把这段也包含进去，
    否则 200 字 snippet 的开头会落在框外。
    """
    result = []
    remaining = size
    for i in range(len(pieces) - 1, -1, -1):
        text, bbox = pieces[i]
        result.append((text, bbox))
        remaining -= len(text)
        if remaining <= 0:
            break
        if i > 0:
            remaining -= 2  # 段落之间的 "\n\n"
        if remaining <= 0:
            break
    result.reverse()
    return result


def _is_double_column(blocks):
    """判断单页是否双栏。

    只看“有效正文块”：长度足够、宽度不像侧边页码/水印。
    左右两栏都要有足够多的块，纵向范围重叠，且合起来跨页高一半以上。
    """
    meaningful = []
    for block in blocks:
        bbox = _block_bbox(block)
        if bbox is None:
            continue
        if len(block["text"]) < COLUMN_MIN_BLOCK_CHARS:
            continue
        if bbox[2] - bbox[0] < COLUMN_MIN_BLOCK_WIDTH:
            continue
        meaningful.append(bbox)

    left = [bbox for bbox in meaningful if bbox[2] <= 0.5]
    right = [bbox for bbox in meaningful if bbox[0] >= 0.5]
    if len(left) < COLUMN_MIN_BLOCKS or len(right) < COLUMN_MIN_BLOCKS:
        return False

    left_y0 = min(bbox[1] for bbox in left)
    left_y1 = max(bbox[3] for bbox in left)
    right_y0 = min(bbox[1] for bbox in right)
    right_y1 = max(bbox[3] for bbox in right)

    overlap = max(left_y0, right_y0) < min(left_y1, right_y1)
    span = max(left_y1, right_y1) - min(left_y0, right_y0)
    return overlap and span >= COLUMN_MIN_SPAN


def build_chunks(blocks):
    """把文字块列表切成 chunk 列表。

    参数:
        blocks: extract_blocks() 返回的文字块列表

    返回:
        chunks: 每个元素包含
            chunk_index / page / content / char_count
            bbox_x0 / bbox_y0 / bbox_x1 / bbox_y1
            bbox_mode: "precise" | "block" | None
    """
    # 1. 按页分组，保持原顺序
    pages = {}
    for block in blocks:
        page_no = block["page"]
        if page_no not in pages:
            pages[page_no] = []
        pages[page_no].append(block)

    # 整篇双栏：双栏页占“有正文的页”一半以上
    body_pages = []
    for page_blocks in pages.values():
        meaningful = [
            block for block in page_blocks
            if len(block["text"]) >= COLUMN_MIN_BLOCK_CHARS and _block_bbox(block) is not None
        ]
        if len(meaningful) >= COLUMN_MIN_BLOCKS:
            body_pages.append(page_blocks)

    document_double_column = (
        bool(body_pages)
        and sum(1 for page_blocks in body_pages if _is_double_column(page_blocks))
        / len(body_pages) >= DOC_DOUBLE_COLUMN_RATIO
    )

    chunks = []
    chunk_index = 0

    for page_no in sorted(pages):
        page_blocks = pages[page_no]
        page_double_column = _is_double_column(page_blocks)

        # 2. 把 block 拆成段落，每个段落继承所在块的 bbox
        paragraphs = [
            (para, _block_bbox(block))
            for block in page_blocks
            for para in block["text"].split("\n\n")
        ]

        # 3. 按 #18 的规则累积成 page_items：
        #    (text, pieces)，pieces 是 [(段落文本, bbox), ...]
        #    文本拼接逻辑必须与旧实现完全一致（700 字上限、长段硬切）。
        page_items = []
        buffer_text = ""
        buffer_pieces = []

        for para, bbox in paragraphs:
            para = para.strip()
            if para == "":
                continue

            # 纯数字短块是页脚页码，丢掉
            if len(para) <= 4 and para.isdigit():
                continue

            # 单段超长：硬切
            while len(para) > TARGET_MAX:
                if buffer_text != "":
                    page_items.append((buffer_text, buffer_pieces))
                    buffer_text = ""
                    buffer_pieces = []
                piece = para[:TARGET_MAX]
                page_items.append((piece, [(piece, bbox)]))
                para = para[TARGET_MAX:]

            if buffer_text == "":
                buffer_text = para
                buffer_pieces = [(para, bbox)]
            elif len(buffer_text) + 2 + len(para) <= TARGET_MAX:
                buffer_text = buffer_text + "\n\n" + para
                buffer_pieces.append((para, bbox))
            else:
                page_items.append((buffer_text, buffer_pieces))
                buffer_text = para
                buffer_pieces = [(para, bbox)]

        if buffer_text != "":
            page_items.append((buffer_text, buffer_pieces))

        # 4. 加重叠并编号
        previous_tail = ""
        previous_tail_pieces = []
        for text, pieces in page_items:
            if previous_tail == "":
                content = text
                content_pieces = list(pieces)
            else:
                content = previous_tail + "\n\n" + text
                content_pieces = previous_tail_pieces + list(pieces)

            content_bboxes = [
                bbox for _piece_text, bbox in content_pieces if bbox is not None
            ]
            bbox = _union_bbox(content_bboxes)

            # 双栏页 / 跨栏 chunk 只能给整段框，老实标 block
            left = any(
                piece_bbox[2] <= 0.52
                and piece_bbox[2] - piece_bbox[0] >= COLUMN_MIN_BLOCK_WIDTH
                for piece_bbox in content_bboxes
            )
            right = any(
                piece_bbox[0] >= 0.48
                and piece_bbox[2] - piece_bbox[0] >= COLUMN_MIN_BLOCK_WIDTH
                for piece_bbox in content_bboxes
            )
            if bbox is None:
                bbox_mode = None
            elif document_double_column or page_double_column or (left and right):
                bbox_mode = "block"
            else:
                bbox_mode = "precise"

            chunks.append({
                "chunk_index": chunk_index,
                "page": page_no,
                "content": content,
                "char_count": len(content),
                "bbox_x0": bbox[0] if bbox is not None else None,
                "bbox_y0": bbox[1] if bbox is not None else None,
                "bbox_x1": bbox[2] if bbox is not None else None,
                "bbox_y1": bbox[3] if bbox is not None else None,
                "bbox_mode": bbox_mode,
            })
            chunk_index = chunk_index + 1

            previous_tail = text[-OVERLAP:]
            previous_tail_pieces = _tail_pieces(pieces, OVERLAP)

    return chunks
