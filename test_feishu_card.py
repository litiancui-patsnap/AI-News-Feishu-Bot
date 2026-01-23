#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试飞书卡片发送"""

import requests
from config import FEISHU_WEBHOOK_URL

def test_simple_card():
    """测试简单卡片（不带图片）"""
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "content": "🤖 测试卡片 - 不带图片",
                    "tag": "plain_text"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": "这是一条测试消息，不包含图片元素",
                        "tag": "plain_text"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "content": "如果你看到这条消息，说明基础卡片功能正常",
                        "tag": "plain_text"
                    }
                }
            ]
        }
    }

    print("发送测试卡片（不带图片）...")
    resp = requests.post(FEISHU_WEBHOOK_URL, json=card)
    print(f"响应状态码: {resp.status_code}")
    print(f"响应内容: {resp.text}")
    return resp.status_code == 200

def test_card_with_image():
    """测试带图片的卡片"""
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "content": "🤖 测试卡片 - 带图片",
                    "tag": "plain_text"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "img",
                    "img_key": "https://raw.githubusercontent.com/litiancui-patsnap/AI-News-Feishu-Bot/main/images/ai_banner.png",
                    "alt": {
                        "tag": "plain_text",
                        "content": "AI资讯日报"
                    },
                    "mode": "fit_horizontal",
                    "preview": True
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "content": "这是一条带图片的测试消息",
                        "tag": "plain_text"
                    }
                }
            ]
        }
    }

    print("\n发送测试卡片（带图片）...")
    resp = requests.post(FEISHU_WEBHOOK_URL, json=card)
    print(f"响应状态码: {resp.status_code}")
    print(f"响应内容: {resp.text}")
    return resp.status_code == 200

def test_text_message():
    """测试纯文本消息"""
    message = {
        "msg_type": "text",
        "content": {
            "text": "这是一条纯文本测试消息"
        }
    }

    print("\n发送纯文本消息...")
    resp = requests.post(FEISHU_WEBHOOK_URL, json=message)
    print(f"响应状态码: {resp.status_code}")
    print(f"响应内容: {resp.text}")
    return resp.status_code == 200

if __name__ == "__main__":
    print("=" * 60)
    print("飞书消息发送测试")
    print("=" * 60)

    # 测试1: 纯文本消息
    print("\n【测试1】纯文本消息")
    test_text_message()

    # 测试2: 简单卡片（不带图片）
    print("\n【测试2】简单卡片（不带图片）")
    test_simple_card()

    # 测试3: 带图片的卡片
    print("\n【测试3】带图片的卡片")
    test_card_with_image()

    print("\n" + "=" * 60)
    print("测试完成！请检查飞书群是否收到3条消息")
    print("=" * 60)
