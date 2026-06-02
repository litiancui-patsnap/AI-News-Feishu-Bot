#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
绿化养护行业信息图生成器

功能：
- 优先使用模板系统（Pillow）生成信息图
- 备用方案：调用 Node.js 图片生成脚本（需要 API）
- 支持多种视觉风格
"""

import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


# 尝试导入模板生成器
INFOGRAPHIC_API_FALLBACK = os.getenv("INFOGRAPHIC_API_FALLBACK", "false").lower() == "true"

try:
    from generate_infographic_template import generate_infographic_template
    TEMPLATE_AVAILABLE = True
except ImportError:
    TEMPLATE_AVAILABLE = False
    print("警告：模板系统不可用，将使用 API 方式")


def generate_infographic_for_news(news_item, output_dir=None, use_template=True):
    """
    为新闻生成信息图

    Args:
        news_item: 新闻数据字典
        output_dir: 输出目录，默认为 ./images/generated
        use_template: 是否使用模板系统（默认 True）

    Returns:
        str: 生成的图片路径，失败返回 None
    """
    # 设置输出目录
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "images", "generated")

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 方案 1：使用模板系统（推荐）
    if use_template and TEMPLATE_AVAILABLE:
        print("使用模板系统生成信息图...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"infographic_{timestamp}.jpg")

        try:
            result = generate_infographic_template(news_item, output_path)
            if result:
                print(f"信息图生成成功: {result}")
                return result
            else:
                print("模板系统生成失败，尝试使用 API 方式...")
        except Exception as e:
            print(f"模板系统出错: {str(e)}，尝试使用 API 方式...")

    # 方案 2：使用 API 方式（备用）
    if not INFOGRAPHIC_API_FALLBACK:
        print("API image fallback disabled; using default banner instead.")
        return None

    return generate_infographic_api(news_item, output_dir)


def build_infographic_prompt(news_item):
    """
    根据新闻内容构建信息图 prompt

    Args:
        news_item: 新闻数据字典，包含 title, summary, category

    Returns:
        str: 适合生成信息图的 prompt
    """
    category = news_item.get('category', '🏞️ 行业动态')
    title = news_item.get('title', '')
    summary = news_item.get('summary', '')

    # 根据分类选择视觉风格
    style_map = {
        '🏞️ 行业动态': '清新绿色主色调，城市绿地和园林轮廓元素',
        '🌿 绿化养护': '植物绿色主色调，草坪、树木、修剪和植保元素',
        '🚿 设备/灌溉': '蓝绿色主色调，灌溉、传感器和园林设备元素',
        '📜 政策/标准': '专业灰绿色，文件、规范和城市管理元素',
        '🏗️ 项目/招采': '商务蓝绿色，项目节点、地图和数据图表元素',
        '🧠 智慧园林': '科技蓝绿色，传感器、AI和智慧园林管理界面元素',
        '🧭 3DGS/空间大模型': '科技蓝绿色，三维高斯、点云、三维重建和空间模型元素'
    }

    style = style_map.get(category, '现代绿色行业信息图，扁平化设计')

    # 提取关键信息（尝试找出数字、百分比等）
    import re
    numbers = re.findall(r'\d+(?:\.\d+)?%?', summary)
    key_numbers = ', '.join(numbers[:3]) if numbers else ''

    # 简化标题（去除过长的内容）
    title_short = title[:60] + '...' if len(title) > 60 else title

    # 提取摘要关键点（最多3个句子）
    summary_sentences = summary.split('。')[:3]
    summary_short = '。'.join(summary_sentences) + '。' if summary_sentences else summary

    prompt = f"""一张中文绿化养护行业信息图（infographic），主题为：「{title_short}」

整体风格：清晰、现代、专业、{style}、扁平插画风格、绿色+蓝色+浅灰色为主色，点缀橙色强调重点、横向构图（16:9），适合企业内部日报分享。

画面结构从左到右分区：
- 左侧标题区：
  * 大标题：{title_short}
  * 分类标签：{category}
  * 日期：今日焦点

- 中部内容区：
  * 核心观点：{summary_short}
  * 关键数据：{key_numbers if key_numbers else '突出重点信息'}
  * 用图标或数字标注要点

- 右侧标识区：
  * 来源："绿化养护行业日报"
  * 简洁的园林、地图或空间技术图标

配色方案：主色调绿色和蓝色，强调色橙色，背景白色或浅灰。
文字要求：中文为主，3DGS、Gaussian Splatting、GIS、BIM、空间大模型等技术术语可保留英文，字体清晰易读。
视觉元素：扁平化图标、简洁几何图形、适当留白。

整体感觉：专业、清爽、面向绿化养护业务，一眼能抓住核心要点，适合快速阅读和分享。"""

    return prompt


def generate_infographic_api(news_item, output_dir):
    """
    使用 API 方式生成信息图（备用方案）

    Args:
        news_item: 新闻数据字典
        output_dir: 输出目录

    Returns:
        str: 生成的图片路径，失败返回 None
    """
    # 构建 prompt
    prompt = build_infographic_prompt(news_item)

    # Node.js 脚本路径
    script_path = os.path.join(
        os.path.dirname(__file__),
        ".claude", ".claude", "scripts", "generate-image.js"
    )

    # API 配置文件路径
    config_path = os.path.join(
        os.path.dirname(__file__),
        ".claude", ".claude", "config", "api-config.json"
    )

    # 检查文件是否存在
    if not os.path.exists(script_path):
        print(f"错误：找不到图片生成脚本: {script_path}")
        return None

    if not os.path.exists(config_path):
        print(f"错误：找不到API配置文件: {config_path}")
        return None

    try:
        print(f"正在生成信息图...")
        print(f"使用脚本: {script_path}")
        print(f"输出目录: {output_dir}")

        # 调用 Node.js 脚本
        result = subprocess.run(
            [
                "node",
                script_path,
                "--config", config_path,
                "--prompt", prompt,
                "--count", "1",
                "--output-dir", output_dir
            ],
            capture_output=True,
            text=True,
            timeout=200,  # 200秒超时
            encoding='utf-8'
        )

        # 打印进度信息（stderr）
        if result.stderr:
            print(result.stderr)

        # 检查执行结果
        if result.returncode != 0:
            print(f"图片生成失败，退出码: {result.returncode}")
            return None

        # 解析 JSON 输出（stdout）
        try:
            output_data = json.loads(result.stdout)
            if output_data and len(output_data) > 0:
                first_result = output_data[0]
                if first_result.get('success'):
                    image_path = first_result.get('path')
                    print(f"✓ 信息图生成成功: {image_path}")
                    return image_path
                else:
                    error_msg = first_result.get('error', '未知错误')
                    print(f"✗ 图片生成失败: {error_msg}")
                    return None
        except json.JSONDecodeError as e:
            print(f"解析输出失败: {e}")
            print(f"原始输出: {result.stdout}")
            return None

    except subprocess.TimeoutExpired:
        print("图片生成超时（200秒）")
        return None
    except Exception as e:
        print(f"生成信息图时出错: {e}")
        return None


def test_generate():
    """测试函数"""
    test_news = {
        'title': '某市启动公园绿地智慧养护试点',
        'summary': '某市园林部门启动智慧养护试点，结合传感器、智能灌溉和三维场景管理提升绿地巡检效率。',
        'category': '🧠 智慧园林'
    }

    print("=" * 60)
    print("测试：生成绿化养护行业信息图")
    print("=" * 60)

    image_path = generate_infographic_for_news(test_news)

    if image_path:
        print(f"\n✅ 测试成功！")
        print(f"图片路径: {image_path}")
        print(f"文件存在: {os.path.exists(image_path)}")
    else:
        print(f"\n❌ 测试失败")
        sys.exit(1)


if __name__ == "__main__":
    # 设置 UTF-8 编码
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    test_generate()
