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
                "content": f"绿化养护行业日报 | <font color='orange'>{date}</font>",
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
                    "content": "绿化养护行业日报"
                },
                "mode": "compact_horizontal",  # 使用紧凑模式，高度最小
                "preview": True
            },
            {
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": "今日精选 3 条行业重要资讯\n🌿 今日行业要点：智慧园林和空间技术正在进入绿化养护场景"
                }
            },
            {
                "tag": "div",
                "text": {
                    "tag": "plain_text",
                    "content": "• 🌿 绿化养护 | 某市发布城市绿化养护标准\n• 🧠 智慧园林 | 智能灌溉平台接入巡检数据\n• 🧭 3DGS/空间大模型 | 3DGS用于绿化资产管理"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**🌿 绿化养护 | 🔥 今日焦点｜某市发布城市绿化养护标准**  [阅读原文 · 示例来源](https://example.com)\n某市园林部门发布新的城市绿化养护标准，覆盖修剪、灌溉和病虫害防治等关键环节。"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**🧠 智慧园林 | 智能灌溉平台接入巡检数据**  [阅读原文 · 示例来源](https://example.com)\n智慧园林平台接入土壤湿度、气象和巡检数据，用于优化绿地浇灌和养护排班。"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**🧭 3DGS/空间大模型 | 3DGS用于绿化资产管理**  [阅读原文 · 示例来源](https://example.com)\n园区项目使用 3DGS 和 GIS 数据构建三维绿化资产台账，支持树木定位和巡检问题追踪。"
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
