#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试飞书图片上传功能"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from ai_news_bot import get_tenant_access_token, upload_image_to_feishu
from config import FEISHU_APP_ID, FEISHU_APP_SECRET

def test_get_token():
    """测试获取访问令牌"""
    print("=" * 60)
    print("测试1: 获取飞书访问令牌")
    print("=" * 60)
    print(f"APP_ID: {FEISHU_APP_ID[:10]}..." if FEISHU_APP_ID else "APP_ID: 未配置")
    print(f"APP_SECRET: {FEISHU_APP_SECRET[:10]}..." if FEISHU_APP_SECRET else "APP_SECRET: 未配置")

    token = get_tenant_access_token()
    if token:
        print(f"✅ 成功获取token: {token[:20]}...")
        return True
    else:
        print("❌ 获取token失败")
        return False

def test_upload_image():
    """测试上传图片"""
    print("\n" + "=" * 60)
    print("测试2: 上传图片到飞书")
    print("=" * 60)

    image_path = os.path.join(os.path.dirname(__file__), "images", "ai_banner.png")
    print(f"图片路径: {image_path}")
    print(f"文件存在: {os.path.exists(image_path)}")

    if not os.path.exists(image_path):
        print("❌ 图片文件不存在")
        return False

    image_key = upload_image_to_feishu(image_path)
    if image_key:
        print(f"✅ 图片上传成功")
        print(f"image_key: {image_key}")
        return image_key
    else:
        print("❌ 图片上传失败")
        return None

def test_send_card_with_image(image_key):
    """测试发送带图片的卡片"""
    print("\n" + "=" * 60)
    print("测试3: 发送带图片的卡片到飞书")
    print("=" * 60)

    import requests
    from config import FEISHU_WEBHOOK_URL

    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "content": "🤖 测试 - 带首图的绿化养护行业日报",
                    "tag": "plain_text"
                },
                "template": "blue"
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
                        "tag": "lark_md",
                        "content": f"✅ 首图功能测试成功！\n\nimage_key: `{image_key}`\n\n[查看测试链接](https://www.feishu.cn)"
                    }
                }
            ]
        }
    }

    resp = requests.post(FEISHU_WEBHOOK_URL, json=card)
    print(f"响应状态码: {resp.status_code}")
    print(f"响应内容: {resp.text}")

    if resp.status_code == 200:
        result = resp.json()
        if result.get("code") == 0:
            print("✅ 卡片发送成功！请检查飞书群")
            return True
        else:
            print(f"❌ 卡片发送失败: {result.get('msg')}")
            return False
    else:
        print("❌ HTTP请求失败")
        return False

if __name__ == "__main__":
    import sys
    import io
    # 设置UTF-8编码输出
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("\n飞书图片上传功能测试\n")

    # 测试1: 获取token
    if not test_get_token():
        print("\n⚠️  请先配置.env文件中的FEISHU_APP_ID和FEISHU_APP_SECRET")
        print("获取方式：https://open.feishu.cn/app")
        sys.exit(1)

    # 测试2: 上传图片
    image_key = test_upload_image()
    if not image_key:
        print("\n❌ 图片上传失败，无法继续测试")
        sys.exit(1)

    # 测试3: 发送带图片的卡片
    test_send_card_with_image(image_key)

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
