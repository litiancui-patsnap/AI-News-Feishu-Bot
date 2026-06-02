#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
绿化养护行业信息图生成器 - 模板系统版本

功能：
- 使用 Pillow 生成信息图
- 基于预设计模板 + 动态文字
- 速度快（<1秒），无 API 成本
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import textwrap


def get_font(size, bold=False):
    """获取字体，优先使用系统中文字体"""
    font_paths = [
        # Windows 字体
        "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
        # Linux 字体
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        # macOS 字体
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue

    # 如果找不到中文字体，使用默认字体
    return ImageFont.load_default()


def wrap_text(text, font, max_width, draw):
    """智能换行文本"""
    lines = []
    paragraphs = text.split('\n')

    for paragraph in paragraphs:
        words = paragraph
        current_line = ""

        for char in words:
            test_line = current_line + char
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]

            if width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char

        if current_line:
            lines.append(current_line)

    return lines


def generate_infographic_template(news_item, output_path):
    """
    使用模板生成信息图

    Args:
        news_item: 新闻数据字典，包含 title, summary, category
        output_path: 输出文件路径

    Returns:
        str: 生成的图片路径，失败返回 None
    """
    try:
        # 提取新闻信息
        title = news_item.get('title', '无标题')
        summary = news_item.get('summary', '')
        category = news_item.get('category', '🏞️ 行业动态')

        # 图片尺寸（16:9）
        width, height = 1200, 675

        # 根据分类选择配色
        color_schemes = {
            '🏞️ 行业动态': {
                'bg': (240, 253, 244),
                'primary': (22, 163, 74),
                'accent': (37, 99, 235),
                'text': (33, 33, 33),
            },
            '🌿 绿化养护': {
                'bg': (236, 253, 245),
                'primary': (5, 150, 105),
                'accent': (245, 158, 11),
                'text': (33, 33, 33),
            },
            '🚿 设备/灌溉': {
                'bg': (240, 248, 255),  # 浅蓝色背景
                'primary': (14, 116, 144),
                'accent': (22, 163, 74),
                'text': (33, 33, 33),  # 深灰色文字
            },
            '📜 政策/标准': {
                'bg': (245, 247, 250),  # 浅灰色背景
                'primary': (71, 85, 105),
                'accent': (22, 163, 74),
                'text': (33, 33, 33),
            },
            '🏗️ 项目/招采': {
                'bg': (240, 253, 250),  # 浅绿色背景
                'primary': (13, 148, 136),
                'accent': (245, 158, 11),
                'text': (33, 33, 33),
            },
            '🧠 智慧园林': {
                'bg': (239, 246, 255),
                'primary': (37, 99, 235),
                'accent': (22, 163, 74),
                'text': (33, 33, 33),
            },
            '🧭 3DJS/空间大模型': {
                'bg': (240, 248, 255),
                'primary': (29, 78, 216),
                'accent': (16, 185, 129),
                'text': (33, 33, 33),
            }
        }

        colors = color_schemes.get(category, color_schemes['🏞️ 行业动态'])

        # 创建画布
        img = Image.new('RGB', (width, height), colors['bg'])
        draw = ImageDraw.Draw(img)

        # 加载字体
        font_title = get_font(42, bold=True)
        font_category = get_font(24)
        font_summary = get_font(28)
        font_footer = get_font(20)

        # 边距
        margin = 50

        # 1. 绘制顶部装饰条
        draw.rectangle([0, 0, width, 10], fill=colors['primary'])

        # 2. 绘制分类标签（左上角）
        category_y = 30
        draw.text((margin, category_y), category, fill=colors['primary'], font=font_category)

        # 3. 绘制"今日焦点"标签（右上角）
        focus_text = "🔥 今日焦点"
        focus_bbox = draw.textbbox((0, 0), focus_text, font=font_category)
        focus_width = focus_bbox[2] - focus_bbox[0]
        draw.text((width - margin - focus_width, category_y), focus_text,
                 fill=colors['accent'], font=font_category)

        # 4. 绘制标题（多行）
        title_y = 100
        title_lines = wrap_text(title[:100], font_title, width - 2 * margin, draw)

        for i, line in enumerate(title_lines[:3]):  # 最多3行
            draw.text((margin, title_y + i * 55), line, fill=colors['text'], font=font_title)

        # 5. 绘制分隔线
        line_y = title_y + len(title_lines[:3]) * 55 + 30
        draw.line([margin, line_y, width - margin, line_y], fill=colors['primary'], width=3)

        # 6. 绘制摘要（多行）
        summary_y = line_y + 40
        summary_lines = wrap_text(summary[:200], font_summary, width - 2 * margin, draw)

        for i, line in enumerate(summary_lines[:5]):  # 最多5行
            draw.text((margin, summary_y + i * 40), line, fill=colors['text'], font=font_summary)

        # 7. 绘制底部信息
        footer_y = height - 60

        # 日期
        date_str = datetime.now().strftime("%Y年%m月%d日")
        draw.text((margin, footer_y), date_str, fill=colors['primary'], font=font_footer)

        # 来源
        source_text = "绿化养护行业日报"
        source_bbox = draw.textbbox((0, 0), source_text, font=font_footer)
        source_width = source_bbox[2] - source_bbox[0]
        draw.text((width - margin - source_width, footer_y), source_text,
                 fill=colors['primary'], font=font_footer)

        # 8. 绘制底部装饰条
        draw.rectangle([0, height - 10, width, height], fill=colors['primary'])

        # 保存图片
        img.save(output_path, 'JPEG', quality=95)
        return output_path

    except Exception as e:
        print(f"生成信息图失败: {str(e)}")
        return None


def test_generate():
    """测试函数"""
    test_news = {
        'title': '某市启动公园绿地智慧养护试点',
        'summary': '某市园林部门启动智慧养护试点，结合传感器、智能灌溉和三维场景管理提升绿地巡检效率。',
        'category': '🧠 智慧园林'
    }

    print("=" * 60)
    print("测试：生成绿化养护行业信息图（模板系统）")
    print("=" * 60)

    output_dir = "./images/generated"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"infographic_template_{timestamp}.jpg")

    result = generate_infographic_template(test_news, output_path)

    if result:
        print(f"\n✅ 测试成功！")
        print(f"图片路径: {result}")
        print(f"文件存在: {os.path.exists(result)}")
    else:
        print(f"\n❌ 测试失败")
        sys.exit(1)


if __name__ == "__main__":
    # 设置 UTF-8 编码
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    test_generate()
