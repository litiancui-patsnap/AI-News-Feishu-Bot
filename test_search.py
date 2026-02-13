#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试搜索关键词效果"""

from ddgs import DDGS
import os
from dotenv import load_dotenv

load_dotenv()

query = os.getenv('SEARCH_QUERY')
print(f'搜索关键词: {query}')
print('=' * 80)

try:
    results = DDGS().text(query, max_results=5)
    for i, r in enumerate(results, 1):
        print(f'\n{i}. {r["title"]}')
        print(f'   URL: {r["href"]}')
        print(f'   摘要: {r["body"][:150]}...')
except Exception as e:
    print(f'搜索失败: {e}')
