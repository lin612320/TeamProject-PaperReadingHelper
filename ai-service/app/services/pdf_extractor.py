"""PDF文本抽取
手段：PyMuPDF 库
作用：FROM .pdf TO text_blocks
"""

import pymupdf

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
        # PyMuPDF 能打开多种格式（如文本、Markdown），这里只接受真正的 PDF
        if not pdf.is_pdf:
            raise ValueError("不是 PDF 文件: " + str(pdf_path))

        # 通过 page_count 方法获取pdf页数
        total_pages = pdf.page_count

        # 清除图片块和空文字块，加入结果文字块序列
        for pno in range(total_pages):
            page = pdf[pno]
            raw_blocks = page.get_text("blocks", sort=True)

            order = 0 # 块计数器
            for block in raw_blocks:
                # 获取 PyMuPDF 文字块的7个固定属性
                x0, y0, x1, y1, text, block_no, block_type = block

                # 跳过非文字块（0=文字，1=图片）
                if block_type != 0:
                    continue

                text = text.strip() # 删去开头结尾的空白字符
                if text == "":
                    continue

                blocks.append({
                    "page": pno + 1,
                    "order": order,
                    "text": text,
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                })
                order = order + 1

    return blocks, total_pages