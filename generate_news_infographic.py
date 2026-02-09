#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI 新闻信息图生成器

功能：
- 根据新闻内容生成专属信息图
- 调用 Node.js 图片生成脚本
- 支持多种视觉风格
"""

import os
import json
import subprocess
import sys
from pathlib import Path


def build_infographic_prompt(news_item):
    """
    根据新闻内容构建信息图 prompt

    Args:
        news_item: 新闻数据字典，包含 title, summary, category

    Returns:
        str: 适合生成信息图的 prompt
    """
    category = news_item.get('category', '🧠 模型/技术')
    title = news_item.get('title', '')
    summary = news_item.get('summary', '')

    # 根据分类选择视觉风格
    style_map = {
        '🖥️ 芯片/硬件': '科技蓝色主色调，电路板纹理背景，硬件图标元素',
        '📜 政策/伦理': '专业灰蓝色，文档和法律图标，严肃专业风格',
        '🏭 产业/公司': '商务蓝绿色渐变，图表和数据可视化元素',
        '🧠 模型/技术': '渐变紫蓝色，神经网络和AI图案，未来科技感',
        '📊 周报/深度': '深蓝色，信息图表风格，数据可视化'
    }

    style = style_map.get(category, '现代科技蓝紫渐变，扁平化设计')

    # 提取关键信息（尝试找出数字、百分比等）
    import re
    numbers = re.findall(r'\d+(?:\.\d+)?%?', summary)
    key_numbers = ', '.join(numbers[:3]) if numbers else ''

    prompt = f"""创建一张专业的中文AI资讯信息图（infographic）：

【标题】{title}

【核心内容】{summary}

【设计要求】
- 整体风格：{style}
- 布局：横向构图（16:9比例），适合社交媒体分享
- 顶部区域：
  * 大标题，使用粗体醒目字体
  * 分类标签：{category}
- 中部区域：
  * 2-3个关键要点，用图标或数字标注
  * 如有数据：{key_numbers if key_numbers else '突出核心观点'}
- 底部区域：
  * 来源标识"AI资讯日报"
  * 日期标记
- 配色方案：
  * 主色调：蓝色系（#2E5BFF, #4A90E2）
  * 强调色：橙色（#FF6B35）用于重点信息
  * 背景：白色或浅灰色（#F5F7FA）
- 文字要求：
  * 中文为主，技术术语保留英文
  * 字体层次清晰：标题>要点>说明
  * 避免文字过多，保持简洁
- 视觉元素：
  * 扁平化图标
  * 简洁的几何图形
  * 适当的留白

【整体感觉】
专业但不严肃，信息密度适中，一眼能抓住核心要点，适合快速阅读和分享。"""

    return prompt


def generate_infographic_for_news(news_item, output_dir=None):
    """
    为新闻生成信息图

    Args:
        news_item: 新闻数据字典
        output_dir: 输出目录，默认为 ./images/generated

    Returns:
        str: 生成的图片路径，失败返回 None
    """
    # 设置输出目录
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "images", "generated")

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

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
        'title': 'OpenAI 发布 GPT-5，性能提升 10 倍',
        'summary': 'OpenAI 今日正式发布 GPT-5 模型，相比 GPT-4 性能提升 10 倍，推理速度提高 50%，成本降低 30%。新模型在数学、编程和多模态理解方面表现出色。',
        'category': '🧠 模型/技术'
    }

    print("=" * 60)
    print("测试：生成 AI 新闻信息图")
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
