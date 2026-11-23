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

# 版面带 / 栏缝参数（#79 #80）
FULL_WIDTH_RATIO = 0.75        # 宽度 > 页宽 75% 的块视为通栏块
NARROW_MAX_WIDTH = 0.55        # 第一遍找候选栏缝时，只信宽度不超过该值的块
GUTTER_SEARCH_MIN = 0.35       # 栏缝搜索区间
GUTTER_SEARCH_MAX = 0.65
GUTTER_STEP = 0.01
GUTTER_MAX_COVERAGE = 1        # 允许跨栏缝的块数（标题/表头偶尔跨过）
GUTTER_MAX_CROSS_SPAN = 0.35   # 跨缝块最多占页高多少；超过说明是通栏表格，不是栏缝
GUTTER_MIN_SIDE_BLOCKS = 2     # 栏缝左右各至少几个块才认


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
    否则 200 字 snippet 的开头会落在框外。每段保留板块的 reading_order，
    供 chunk 取“首块顺序”。
    """
    result = []
    remaining = size
    for i in range(len(pieces) - 1, -1, -1):
        text, bbox, order = pieces[i]
        result.append((text, bbox, order))
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


# ────────────────────────────────────────────────────────────
# #79 / #80：版面带与栏缝
#   这些函数只产出“版面判定”，不改 build_chunks 的切片结果；
#   真正按 band/column 重排、写 reading_order 是 #81。
# ────────────────────────────────────────────────────────────

def _block_width(block):
    """返回归一化宽度；bbox 非法时返回 None。"""
    bbox = _block_bbox(block)
    if bbox is None:
        return None
    return bbox[2] - bbox[0]


def _is_full_width_block(block):
    """宽度超过页宽 75% 的块：通栏标题、通栏图注、通栏表格等。

    注意：这是几何判定，不是语义分类。它只说明这个块横跨了
    大部分页宽、不能完整放进某一栏，并不保证它一定是标题/图/表。
    """
    width = _block_width(block)
    return width is not None and width > FULL_WIDTH_RATIO


def _crosses(block, x):
    """块是否横跨给定的 x（x 落在块的左右边界之间）。"""
    bbox = _block_bbox(block)
    return bbox is not None and bbox[0] < x < bbox[2]


def _has_valid_bbox(blocks):
    """这一组块里是否至少有一个可用 bbox。"""
    for block in blocks:
        if _block_bbox(block) is not None:
            return True
    return False


def _is_layout_block(block):
    """宽度达到一个栏内文字块的最小宽度，排除图表里的碎词。"""
    width = _block_width(block)
    return width is not None and width >= COLUMN_MIN_BLOCK_WIDTH


def _is_meaningful_block(block):
    """够长、够宽的有效正文块；用于栏缝证据，避免表头/图表碎词干扰。"""
    if not _is_layout_block(block):
        return False
    return len(block.get("text") or "") >= COLUMN_MIN_BLOCK_CHARS


def _band_bounds(blocks):
    """返回 band 的纵向范围 (min y0, max y1)；没有有效 bbox 时返回 (None, None)。"""
    y0 = None
    y1 = None
    for block in blocks:
        bbox = _block_bbox(block)
        if bbox is None:
            continue
        if y0 is None or bbox[1] < y0:
            y0 = bbox[1]
        if y1 is None or bbox[3] > y1:
            y1 = bbox[3]
    return y0, y1


def _runs(xs, counts, value):
    """把 counts 中连续等于 value 的点合并成区间。

    返回 [(start_x, end_x), ...]，按 x 从左到右。
    """
    runs = []
    start = None
    for i, count in enumerate(counts):
        if count == value:
            if start is None:
                start = i
        else:
            if start is not None:
                runs.append((xs[start], xs[i - 1]))
                start = None
    if start is not None:
        runs.append((xs[start], xs[-1]))
    return runs


def _run_midpoint(run):
    """取区间的中点，保留两位小数。"""
    return round((run[0] + run[1]) / 2.0, 2)


def _widest_run(runs):
    """取最宽的区间；同宽时取离 0.5 最近的，保证结果确定。"""
    best = None
    for run in runs:
        if best is None:
            best = run
            continue
        width = run[1] - run[0]
        best_width = best[1] - best[0]
        if width > best_width + 1e-9:
            best = run
        elif abs(width - best_width) <= 1e-9:
            if abs(_run_midpoint(run) - 0.5) < abs(_run_midpoint(best) - 0.5):
                best = run
    return best


def _gutter_profile(blocks):
    """把块的 [x0, x1] 投影到 0.35–0.65 的横轴上，统计覆盖次数。

    返回:
        {
            "xs": [...], "counts": [...],
            "min_count": int, "min_xs": [...],
            "zero_runs": [(start, end), ...],
            "min_runs": [(start, end), ...],
        }
    """
    xs = []
    counts = []
    steps = int(round((GUTTER_SEARCH_MAX - GUTTER_SEARCH_MIN) / GUTTER_STEP))

    for i in range(steps + 1):
        x = round(GUTTER_SEARCH_MIN + i * GUTTER_STEP, 4)
        count = 0
        for block in blocks:
            bbox = _block_bbox(block)
            if bbox is not None and bbox[0] < x < bbox[2]:
                count += 1
        xs.append(x)
        counts.append(count)

    min_count = min(counts) if counts else 0
    min_xs = [xs[i] for i, count in enumerate(counts) if count == min_count]

    return {
        "xs": xs,
        "counts": counts,
        "min_count": min_count,
        "min_xs": min_xs,
        "zero_runs": _runs(xs, counts, 0),
        "min_runs": _runs(xs, counts, min_count),
    }


def _side_counts(blocks, x):
    """栏缝左右两侧各有多少个块（跨栏缝的块不计入任何一侧）。"""
    left = 0
    right = 0
    for block in blocks:
        bbox = _block_bbox(block)
        if bbox is None:
            continue
        if bbox[2] <= x:
            left += 1
        elif bbox[0] >= x:
            right += 1
    return left, right


def _cross_span(blocks, x):
    """跨过 x 的块在纵向覆盖了多高（0~1）。

    标题、表头可能只在一小段高度上跨过中线；真正填满整栏的通栏表格
    会跨过大部分页高。用它区分“可以容忍的少量跨栏”和“这不是栏缝”。
    """
    intervals = []
    for block in blocks:
        bbox = _block_bbox(block)
        if bbox is not None and bbox[0] < x < bbox[2]:
            intervals.append((bbox[1], bbox[3]))

    if not intervals:
        return 0.0

    intervals.sort()
    total = 0.0
    start, end = intervals[0]
    for y0, y1 in intervals[1:]:
        if y0 <= end:
            if y1 > end:
                end = y1
        else:
            total += end - start
            start, end = y0, y1
    total += end - start
    return total


def _choose_gutter(profile, blocks):
    """从投影结果里选栏缝；找不到合格栏缝时返回 None。"""
    runs = profile["zero_runs"]
    if runs:
        run = _widest_run(runs)
        coverage = 0
        method = "zero_gap"
    elif profile["min_count"] <= GUTTER_MAX_COVERAGE:
        run = _widest_run(profile["min_runs"])
        coverage = profile["min_count"]
        method = "min_coverage"
    else:
        # 少量块跨过栏缝（标题行、表头）：只要它们纵向只占一小段，
        # 仍然可以认这条栏缝；通栏表格会占掉大半页高，会被排除。
        short_runs = []
        for candidate_run in profile["min_runs"]:
            x = _run_midpoint(candidate_run)
            if _cross_span(blocks, x) <= GUTTER_MAX_CROSS_SPAN:
                short_runs.append(candidate_run)
        if not short_runs:
            return None
        run = _widest_run(short_runs)
        coverage = profile["min_count"]
        method = "short_crossings"

    x = _run_midpoint(run)
    left, right = _side_counts(blocks, x)
    if left < GUTTER_MIN_SIDE_BLOCKS or right < GUTTER_MIN_SIDE_BLOCKS:
        return None

    return {
        "x": x,
        "coverage": coverage,
        "left": left,
        "right": right,
        "crossSpan": round(_cross_span(blocks, x), 3),
        "method": method,
    }


def _find_candidate_gutter(page_blocks):
    """第一遍：只用窄块找候选栏缝，避免表格行/标题污染投影。

    找不到候选栏缝时，这一页按单栏处理，不做任何切带。
    """
    narrow = []
    for block in page_blocks:
        width = _block_width(block)
        if (
            width is not None
            and width <= NARROW_MAX_WIDTH
            and _is_meaningful_block(block)
        ):
            narrow.append(block)

    if len(narrow) < GUTTER_MIN_SIDE_BLOCKS * 2:
        return None

    profile = _gutter_profile(narrow)
    return _choose_gutter(profile, narrow)


def _detect_gutter(band_blocks):
    """在一个带内找栏间空白（gutter）；单栏带返回 None。"""
    meaningful = [block for block in band_blocks if _is_meaningful_block(block)]
    if len(meaningful) < GUTTER_MIN_SIDE_BLOCKS * 2:
        return None
    profile = _gutter_profile(meaningful)
    return _choose_gutter(profile, meaningful)


def _split_bands(page_blocks, candidate_gutter=None):
    """按通栏块 / 跨栏块把一页切成若干横带（#79 #80）。

    参数:
        page_blocks: 一页的 block 列表
        candidate_gutter: 候选栏缝 x；传入时，跨过它的块也作为切带屏障

    返回:
        [
            {
                "blocks": [...],       # 保持输入顺序
                "full_width": bool,    # 是否是横跨整页的屏障带
                "y0": float | None,
                "y1": float | None,
            },
            ...
        ]
        带序自上而下；块只换带，不丢、不重、不修改。
    """
    valid = []
    invalid = []
    for index, block in enumerate(page_blocks):
        if _block_bbox(block) is None:
            invalid.append((index, block))
        else:
            valid.append((index, block))

    if not valid:
        return [{
            "blocks": list(page_blocks),
            "full_width": False,
            "y0": None,
            "y1": None,
        }]

    ordered = sorted(
        valid,
        key=lambda item: (
            _block_bbox(item[1])[1],
            _block_bbox(item[1])[0],
            item[0],
        ),
    )

    band_id = [0] * len(page_blocks)
    bands = []

    for index, block in ordered:
        barrier = _is_full_width_block(block)
        if (
            candidate_gutter is not None
            and _is_layout_block(block)
            and _crosses(block, candidate_gutter)
        ):
            barrier = True

        if barrier:
            # 连续屏障（例如表格的多行）合并成一个带
            if bands and bands[-1]["full_width"]:
                band_id[index] = len(bands) - 1
            else:
                bands.append({"blocks": [], "full_width": True})
                band_id[index] = len(bands) - 1
        else:
            if not bands or bands[-1]["full_width"]:
                bands.append({"blocks": [], "full_width": False})
            band_id[index] = len(bands) - 1

    # bbox 非法的块无法参与排序：挂到它前面最近的有效块所属的带，
    # 保证不丢块，也不把顺序整体打乱。
    last_band = 0
    for index, block in enumerate(page_blocks):
        if _block_bbox(block) is not None:
            last_band = band_id[index]
        else:
            band_id[index] = last_band

    # 按原始顺序回填：单栏页只有一个带时，块顺序与输入完全一致
    for index, block in enumerate(page_blocks):
        bands[band_id[index]]["blocks"].append(block)

    for band in bands:
        y0, y1 = _band_bounds(band["blocks"])
        band["y0"] = y0
        band["y1"] = y1

    return bands


def build_page_layout(page_blocks):
    """返回一页的版面结构（#79 #80 的集成入口）。

    输出:
        {
            "layout": "single" | "double" | "unknown",
            "candidateGutter": float | None,
            "bands": [
                {
                    "blocks": [...],
                    "full_width": bool,
                    "y0": float | None,
                    "y1": float | None,
                    "gutter": float | None,
                    "layout": "full_width" | "double" | "single" | "unknown",
                },
                ...
            ],
        }

    单栏守卫：找不到候选栏缝时，整页一个带、保持原顺序；
    这样单栏论文即使正文块很宽，也不会被误切。
    """
    candidate = _find_candidate_gutter(page_blocks)

    if candidate is None:
        blocks = list(page_blocks)
        y0, y1 = _band_bounds(blocks)
        layout = "single" if _has_valid_bbox(blocks) else "unknown"
        return {
            "layout": layout,
            "candidateGutter": None,
            "bands": [{
                "blocks": blocks,
                "full_width": False,
                "y0": y0,
                "y1": y1,
                "gutter": None,
                "layout": layout,
            }],
        }

    bands = _split_bands(page_blocks, candidate["x"])
    has_double = False

    for band in bands:
        if band["full_width"]:
            band["gutter"] = None
            band["layout"] = "full_width"
            continue

        gutter = _detect_gutter(band["blocks"])
        if gutter is None:
            band["gutter"] = None
            band["layout"] = "single"
        else:
            band["gutter"] = gutter["x"]
            band["layout"] = "double"
            has_double = True

    return {
        "layout": "double" if has_double else "single",
        "candidateGutter": candidate["x"],
        "bands": bands,
    }


def _block_sort_key(block, index):
    """按 (y0, x0, 原始下标) 排序；bbox 非法的块排在本带末尾。"""
    bbox = _block_bbox(block)
    if bbox is None:
        return (1.0, 1.0, index)
    return (bbox[1], bbox[0], index)


def _order_page_blocks(page_blocks, layout):
    """按 (band, column, y0, x0) 返回 [(block, reading_order), ...]。

    - 单栏/unknown 页：保持提取顺序，reading_order 从 0 递增。
    - 双栏页：按 band 自上而下；双栏带内先左栏后右栏，
      跨栏块（column=-1）排在本带末尾。
    """
    if layout["layout"] != "double":
        return [(block, index) for index, block in enumerate(page_blocks)]

    ordered = []
    for band in layout["bands"]:
        band_blocks = band["blocks"]
        if band["layout"] != "double":
            sorted_band = sorted(
                enumerate(band_blocks),
                key=lambda item: _block_sort_key(item[1], item[0]),
            )
            ordered.extend(block for _index, block in sorted_band)
            continue

        gutter = band["gutter"]

        def band_key(item):
            index, block = item
            bbox = _block_bbox(block)
            if bbox is None:
                return (2, 1.0, 1.0, index)
            if bbox[2] <= gutter:
                column = 0
            elif bbox[0] >= gutter:
                column = 1
            else:
                column = 2  # 跨栏块排本带末尾（契约里的 column=-1）
            return (column, bbox[1], bbox[0], index)

        sorted_band = sorted(enumerate(band_blocks), key=band_key)
        ordered.extend(block for _index, block in sorted_band)

    # 防御：layout 理论上覆盖全部块；若有遗漏，按原顺序补在末尾
    if len(ordered) != len(page_blocks):
        seen = set(id(block) for block in ordered)
        for block in page_blocks:
            if id(block) not in seen:
                ordered.append(block)

    return [(block, index) for index, block in enumerate(ordered)]


def build_chunks(blocks):
    """把文字块列表切成 chunk 列表。

    参数:
        blocks: extract_blocks() 返回的文字块列表

    返回:
        chunks: 每个元素包含
            chunk_index / page / content / char_count
            bbox_x0 / bbox_y0 / bbox_x1 / bbox_y1
            bbox_mode: "precise" | "block" | None
            reading_order: 页内阅读顺序（#81），从 0 起
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

        # 2. #81：按 (band, column, y0, x0) 排本页块；单栏页保持原顺序
        page_layout = build_page_layout(page_blocks)
        ordered_blocks = _order_page_blocks(page_blocks, page_layout)

        # 3. 把 block 拆成段落，每个段落继承所在块的 bbox 和 reading_order
        paragraphs = [
            (para, _block_bbox(block), order)
            for block, order in ordered_blocks
            for para in block["text"].split("\n\n")
        ]

        # 4. 按 #18 的规则累积成 page_items：
        #    (text, pieces)，pieces 是 [(段落文本, bbox, reading_order), ...]
        #    文本拼接逻辑必须与旧实现完全一致（700 字上限、长段硬切）。
        page_items = []
        buffer_text = ""
        buffer_pieces = []

        for para, bbox, order in paragraphs:
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
                page_items.append((piece, [(piece, bbox, order)]))
                para = para[TARGET_MAX:]

            if buffer_text == "":
                buffer_text = para
                buffer_pieces = [(para, bbox, order)]
            elif len(buffer_text) + 2 + len(para) <= TARGET_MAX:
                buffer_text = buffer_text + "\n\n" + para
                buffer_pieces.append((para, bbox, order))
            else:
                page_items.append((buffer_text, buffer_pieces))
                buffer_text = para
                buffer_pieces = [(para, bbox, order)]

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
                bbox for _piece_text, bbox, _order in content_pieces
                if bbox is not None
            ]
            bbox = _union_bbox(content_bboxes)
            reading_order = content_pieces[0][2] if content_pieces else None

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
                "reading_order": reading_order,
            })
            chunk_index = chunk_index + 1

            previous_tail = text[-OVERLAP:]
            previous_tail_pieces = _tail_pieces(pieces, OVERLAP)

    return chunks
