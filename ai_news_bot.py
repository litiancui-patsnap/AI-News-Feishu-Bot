from scrapegraphai.graphs import SmartScraperGraph
from ddgs import DDGS
from config import OLLAMA_CONFIG, FEISHU_WEBHOOK_URL, MAX_NEWS_ITEMS, SEARCH_QUERY
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
            messages=[{'role': 'user', 'content': f'提取以下AI资讯的核心观点和关键信息,用中文总结成2-3句话,突出新闻价值:\n{text}'}]
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

def clean_title(title):
    """清理标题,移除网站名称后缀"""
    import re
    # 移除常见的分隔符及其后的内容
    patterns = [r'\s*[|\-–—]\s*[A-Za-z\s]+$', r'\s*\|\s*.+$']
    for pattern in patterns:
        title = re.sub(pattern, '', title)
    return title.strip()

def extract_source(url):
    """从URL提取来源网站名称"""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    # 移除www.和常见后缀
    domain = domain.replace('www.', '').split('.')[0]
    return domain.capitalize()

def get_topic_emoji(title, summary):
    """根据标题和摘要推断主题emoji"""
    text = (title + ' ' + summary).lower()

    # 按优先级匹配关键词
    if any(word in text for word in ['融资', '投资', '收购', 'funding', 'investment', 'acquisition']):
        return '💰'
    elif any(word in text for word in ['发布', '推出', 'launch', 'release', 'announce']):
        return '🚀'
    elif any(word in text for word in ['监管', '法规', '政策', 'regulation', 'policy', 'law']):
        return '⚖️'
    elif any(word in text for word in ['突破', '创新', 'breakthrough', 'innovation']):
        return '🔬'
    elif any(word in text for word in ['模型', 'gpt', 'llm', 'model', 'ai']):
        return '🤖'
    else:
        return '📰'

def truncate_text(text, max_len):
    """智能截断文本,在标点符号处截断"""
    if len(text) <= max_len:
        return text
    # 在标点符号处截断
    truncated = text[:max_len]
    for punct in ['。', '！', '？', '.', '!', '?', '，', ',']:
        last_punct = truncated.rfind(punct)
        if last_punct > max_len * 0.6:  # 至少保留60%的内容
            return truncated[:last_punct + 1]
    return truncated + "..."

def send_to_feishu(news_items):
    """发送卡片消息到飞书"""
    from datetime import datetime
    date = datetime.now().strftime("%Y.%m.%d")

    # 生成3个要点
    key_points = "\n".join([f"• {truncate_text(clean_title(item['title']), 50)}" for item in news_items[:3]])

    # 顶部总览卡片
    overview_card = {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": f"🤖 AI资讯日报 | {date}"}, "template": "blue"},
            "elements": [
                {"tag": "div", "text": {"tag": "plain_text", "content": f"今日精选 {len(news_items)} 条AI行业重要资讯"}},
                {"tag": "div", "text": {"tag": "lark_md", "content": key_points}}
            ]
        }
    }

    # 发送总览卡片
    resp = requests.post(FEISHU_WEBHOOK_URL, json=overview_card)
    print(f"发送总览卡片: {resp.status_code}")
    time.sleep(0.5)

    # Top文章卡片
    for idx, item in enumerate(news_items, 1):
        title = truncate_text(clean_title(item['title']), 80)
        summary = truncate_text(item['summary'], 150)
        source = extract_source(item['url'])
        emoji = get_topic_emoji(item['title'], item['summary'])

        article_card = {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": f"{emoji} Top文章 {idx}"}, "template": "grey"},
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md", "content": f"**{title}**"}},
                    {"tag": "div", "text": {"tag": "plain_text", "content": summary}},
                    {"tag": "note", "elements": [{"tag": "plain_text", "content": f"来源: {source}"}]},
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
    search_results = search_ai_news(SEARCH_QUERY, max_results=MAX_NEWS_ITEMS)

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
