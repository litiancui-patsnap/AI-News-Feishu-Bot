#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试特定image_key的卡片"""

import sys
import io
import requests
from datetime import datetime
from config import FEISHU_WEBHOOK_URL

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 使用指定的image_key
image_key = "img_v3_02u7_e686a2ac-64c7-4b64-8bd0-1f9b6f11d11g"
date = datetime.now().strftime("%Y/%m/%d")

card = {
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {
                "content": f"AI资讯日报 | <font color='orange'>{date}</font>",
                "tag": "lark_md"
            },
            "template": "blue",
            "ud_icon": {
                "tag": "img",
                "img_key": "img_v3_02u7_3dfb2d58-1885-400f-9278-4c049e5d908g"
            }
        },
        "elements": [
            {
                "tag": "img",
                "img_key": image_key,
                "alt": {
                    "tag": "plain_text",
                    "content": "AI资讯日报"
                },
                "mode": "compact_horizontal",  # 使用紧凑模式，高度最小
                "preview": True
            },
            {
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": "今日精选 3 条AI行业重要资讯\n🧠 今日AI要点：AI技术在多个领域取得突破性进展"
                }
            },
            {
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": "• 🧠 模型/技术 | OpenAI发布新一代GPT模型\n• 🏭 产业/公司 | 微软AI业务增长超预期\n• 📜 政策/伦理 | 欧盟通过AI监管新法案"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**🧠 模型/技术 | 🔥 今日焦点｜OpenAI发布新一代GPT模型**  [阅读原文 · Techcrunch](https://techcrunch.com)\nOpenAI今日发布了新一代GPT模型，在推理能力和多模态理解方面取得重大突破，性能提升显著。"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**🏭 产业/公司 | 微软AI业务增长超预期**  [阅读原文 · Microsoft](https://microsoft.com)\n微软最新财报显示，其AI相关业务收入同比增长超过50%，Azure AI服务成为主要增长引擎。"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**📜 政策/伦理 | 欧盟通过AI监管新法案**  [阅读原文 · Reuters](https://reuters.com)\n欧盟议会正式通过AI监管法案，对高风险AI应用实施严格监管，将于2026年全面生效。"
                }
            }
        ]
    }
}

print("发送测试卡片（使用指定image_key）...")
print(f"image_key: {image_key}")
resp = requests.post(FEISHU_WEBHOOK_URL, json=card)
print(f"响应状态码: {resp.status_code}")
print(f"响应内容: {resp.text}")

if resp.status_code == 200:
    result = resp.json()
    if result.get("code") == 0:
        print("✅ 卡片发送成功！请检查飞书群")
    else:
        print(f"❌ 卡片发送失败: {result.get('msg')}")
else:
    print("❌ HTTP请求失败")
