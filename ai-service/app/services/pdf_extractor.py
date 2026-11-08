"""PDF文本抽取
手段：PyMuPDF 库
作用：FROM .pdf TO text_blocks
"""

import re
import pymupdf


def _normalize_rect(rect, page_width, page_height):
    """把 PyMuPDF 的绝对坐标转成 0~1 的归一化 bbox。

    参数:
        rect: 已经过 rotation_matrix 变换的可视坐标
        page_width / page_height: page.rect 的宽高（旋转后）

    返回:
        (x0, y0, x1, y1)；无效时返回 (None, None, None, None)
    """
    if page_width <= 0 or page_height <= 0:
        return (None, None, None, None)

    # 归一化后限制在 0~1，避免旋转/浮点误差导致越界
    x0 = min(max(rect.x0 / page_width, 0.0), 1.0)
    y0 = min(max(rect.y0 / page_height, 0.0), 1.0)
    x1 = min(max(rect.x1 / page_width, 0.0), 1.0)
    y1 = min(max(rect.y1 / page_height, 0.0), 1.0)

    # 契约要求宽高为正；退化块不要写入非法坐标
    if x1 <= x0 or y1 <= y0:
        return (None, None, None, None)
    return (x0, y0, x1, y1)


def extract_blocks(pdf_path):
    """从指定路径抽取pdf的文字块和页数。

    参数:
        pdf_path: 指定路径

    返回:
        blocks：返回的PyMuPDF文字块
        total_pages：返回的pdf总页数
    """
    blocks = []
    # 以 PyMuPDF 的方式打开.pdf文件
    with pymupdf.open(pdf_path) as pdf:
        if not pdf.is_pdf:
            raise ValueError("不是 PDF 文件: " + str(pdf_path))

        # 通过 page_count 方法获取pdf页数
        total_pages = pdf.page_count

        # 清除图片块和空文字块，加入结果文字块序列
        for pno in range(total_pages):
            page = pdf[pno]
            raw_blocks = page.get_text("blocks", sort=True)

            # page.rect 已含旋转；但 get_text("blocks") 返回的是未旋转坐标，
            # 必须先乘 rotation_matrix 转成用户看到的可视坐标，再除以 page.rect。
            page_width = page.rect.width
            page_height = page.rect.height
            rotation_matrix = page.rotation_matrix

            order = 0 # 块计数器
            for block in raw_blocks:
                # 获取 PyMuPDF 文字块的7个固定属性
                x0, y0, x1, y1, text, block_no, block_type = block

                # 跳过非文字块（0=文字，1=图片）
                if block_type != 0:
                    continue

                # 去掉 NUL 等控制字符：PostgreSQL 的 text 字段不接受 0x00
                text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
                text = text.strip() # 删去开头结尾的空白字符
                if text == "":
                    continue

                # 旋转页：先转坐标，再归一化（契约 0~1、左上原点、相对当页）
                visible_rect = pymupdf.Rect(x0, y0, x1, y1) * rotation_matrix
                bbox_x0, bbox_y0, bbox_x1, bbox_y1 = _normalize_rect(
                    visible_rect, page_width, page_height
                )

                blocks.append({
                    "page": pno + 1,
                    "order": order,
                    "text": text,
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                    # 归一化 bbox，供切片和引用高亮使用（#40）
                    "bbox_x0": bbox_x0,
                    "bbox_y0": bbox_y0,
                    "bbox_x1": bbox_x1,
                    "bbox_y1": bbox_y1,
                })
                order = order + 1

    return blocks, total_pages