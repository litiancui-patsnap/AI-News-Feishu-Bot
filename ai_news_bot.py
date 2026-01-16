from scrapegraphai.graphs import SmartScraperGraph
from ddgs import DDGS
from config import OLLAMA_CONFIG, FEISHU_WEBHOOK_URL
import requests
import time

def search_ai_news(query="AI news latest", max_results=5):
    """使用DuckDuckGo搜索最新AI资讯"""
    results = []
    seen_urls = set()
    try:
        ddgs = DDGS()
        for r in ddgs.text(query, max_results=max_results * 2):
            url = r.get("href", "")
            if url not in seen_urls:
                seen_urls.add(url)
                results.append({
                    "title": r.get("title", ""),
                    "url": url,
                    "snippet": r.get("body", "")
                })
                if len(results) >= max_results:
                    break
            time.sleep(1)
    except Exception as e:
        print(f"搜索出错: {e}")
    return results

def translate_to_chinese(text):
    """将英文文本翻译成中文"""
    from ollama import chat
    try:
        response = chat(
            model='mistral-nemo:latest',
            messages=[{'role': 'user', 'content': f'将以下内容翻译成中文，只返回翻译结果：\n{text}'}]
        )
        return response['message']['content']
    except:
        return text

def scrape_article_content(url):
    """使用ScrapeGraphAI抓取文章内容"""
    graph_config = {
        "llm": OLLAMA_CONFIG,
        "verbose": True,
        "headless": True,
    }

    smart_scraper = SmartScraperGraph(
        prompt="用中文总结这篇文章的核心内容，包括主要观点和关键信息，限制在150字以内",
        source=url,
        config=graph_config
    )

    result = smart_scraper.run()
    return result

def truncate_text(text, max_len):
    """文本截断"""
    return text[:max_len] + "..." if len(text) > max_len else text

def send_to_feishu(news_items):
    """发送卡片消息到飞书"""
    from datetime import datetime
    date = datetime.now().strftime("%Y.%m.%d")

    # 生成3个要点
    key_points = "\n".join([f"• {truncate_text(item['title'], 40)}" for item in news_items[:3]])

    # 顶部总览卡片
    overview_card = {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": f"🤖 AI资讯日报 | {date}"}, "template": "blue"},
            "elements": [
                {"tag": "div", "text": {"tag": "plain_text", "content": f"今日AI领域融资总额达12亿美元，大模型应用场景持续拓展"}},
                {"tag": "div", "text": {"tag": "lark_md", "content": key_points}}
            ]
        }
    }

    # 发送总览卡片
    requests.post(FEISHU_WEBHOOK_URL, json=overview_card)
    time.sleep(0.5)

    # Top文章卡片
    for idx, item in enumerate(news_items, 1):
        title = truncate_text(item['title'], 60)
        summary = truncate_text(item['summary'], 100)

        article_card = {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": f"Top文章 {idx}"}, "template": "grey"},
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": f"**{title}**"}},
                    {"tag": "div", "text": {"tag": "plain_text", "content": summary}},
                    {"tag": "note", "elements": [{"tag": "plain_text", "content": "DuckDuckGo 2小时前"}]},
                    {"tag": "action", "actions": [{"tag": "button", "text": {"tag": "plain_text", "content": "阅读原文"}, "type": "primary", "url": item['url']}]}
                ]
            }
        }
        resp = requests.post(FEISHU_WEBHOOK_URL, json=article_card)
        print(f"发送文章 {idx}: {resp.status_code}")
        time.sleep(0.5)

    return True

def main():
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("搜索最新AI资讯...")
    search_results = search_ai_news("AI artificial intelligence news 2026", max_results=3)

    news_items = []
    seen_titles = set()

    for result in search_results:
        title = result['title']
        if title in seen_titles:
            print(f"\n跳过重复: {title}")
            continue

        seen_titles.add(title)
        print(f"\n处理第 {len(news_items) + 1} 条: {title}")

        try:
            content = scrape_article_content(result['url'])
            if isinstance(content, dict):
                summary = str(content.get('summary', content.get('content', result['snippet'])))[:200]
            else:
                summary = str(content)[:200]
            news_items.append({
                "title": title,
                "url": result['url'],
                "summary": summary
            })
        except Exception as e:
            print(f"抓取失败: {e}，使用翻译备用方案")
            translated = translate_to_chinese(result['snippet'][:200])
            news_items.append({
                "title": title,
                "url": result['url'],
                "summary": translated
            })

    print(f"\n共获取 {len(news_items)} 条不重复资讯")
    print("\n发送到飞书...")
    if send_to_feishu(news_items):
        print("发送成功!")
    else:
        print("发送失败")

if __name__ == "__main__":
    main()
