from scrapegraphai.graphs import SmartScraperGraph
from ddgs import DDGS
from config import OLLAMA_CONFIG, FEISHU_WEBHOOK_URL, MAX_NEWS_ITEMS, SEARCH_QUERY
import requests
import time
from datetime import datetime

def is_recent_article(url):
    """检查文章是否为最近3天内的"""
    import re
    # 提取URL中的日期模式
    date_patterns = [
        r'/(\d{4})/(\d{2})/(\d{2})/',  # /2026/01/19/
        r'/(\d{4})-(\d{2})-(\d{2})',    # /2026-01-19
        r'(\d{4})(\d{2})(\d{2})',       # 20260119
    ]

    for pattern in date_patterns:
        match = re.search(pattern, url)
        if match:
            try:
                year, month, day = match.groups()
                article_date = datetime(int(year), int(month), int(day))
                days_old = (datetime.now() - article_date).days
                return days_old <= 3
            except:
                continue

    # 如果URL中没有日期，默认认为是最新的
    return True

def search_ai_news(query="AI news latest", max_results=5):
    """使用DuckDuckGo搜索最新AI资讯"""
    results = []
    seen_urls = set()
    try:
        ddgs = DDGS()
        # 增加搜索范围到5倍，确保过滤后仍有足够结果
        for r in ddgs.text(query, max_results=max_results * 5):
            url = r.get("href", "")
            if url not in seen_urls and is_url_accessible(url) and is_recent_article(url):
                seen_urls.add(url)
                results.append({
                    "title": r.get("title", ""),
                    "url": url,
                    "snippet": r.get("body", "")
                })
                if len(results) >= max_results:
                    break
            time.sleep(0.5)
    except Exception as e:
        print(f"搜索出错: {e}")
    return results

def is_url_accessible(url):
    """检查URL是否可访问且为有效文章"""
    # 过滤分类页、标签页、列表页、新闻汇总等非文章URL
    excluded_patterns = [
    '/category/', '/tag/', '/tags/', '/topics/', '/author/', '/page/',
    '/tagged/', '/news/', '/headlines/', '/ai-news', '/blog/', '/archive/',
    'roundup', 'weekly'
]

    if any(pattern in url.lower() for pattern in excluded_patterns):
        return False

    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code < 400
    except:
        return False

def translate_to_chinese(text):
    """将英文文本翻译成中文"""
    from ollama import chat
    try:
        response = chat(
            model='mistral-nemo:latest',
            messages=[{'role': 'user', 'content': f'提取以下AI资讯的核心观点和关键信息,用中文总结成2-3句话,突出新闻价值:\n{text}'}]
        )
        return response['message']['content']
    except Exception as e:
        print(f"翻译失败: {e}")
        return text

def scrape_article_content(url):
    """使用ScrapeGraphAI抓取文章内容"""
    graph_config = {
        "llm": OLLAMA_CONFIG,
        "verbose": True,
        "headless": True,
    }

    smart_scraper = SmartScraperGraph(
        prompt="""请用中文生成一段"读完即够"的AI资讯摘要：
优先提炼文章的核心结论、最新信息和实际影响，忽略背景铺垫、作者介绍、广告和无关内容。
用2–3句话完整表达"发生了什么 + 为什么重要/影响谁"，如有明确数据、时间或主体请保留。
总字数不超过150字。""",
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
    """根据标题和摘要推断主题分类标签"""
    text = (title + ' ' + summary).lower()

    if any(word in text for word in ['chip', 'gpu', 'nvidia', 'amd', '芯片', '硬件', 'hardware']):
        return '🖥️ 芯片/硬件'
    elif any(word in text for word in ['regulation', 'policy', 'law', '监管', '法规', '政策', '伦理']):
        return '📜 政策/伦理'
    elif any(word in text for word in ['funding', 'investment', 'acquisition', 'company', '融资', '投资', '收购', '公司', '产业']):
        return '🏭 产业/公司'
    elif any(word in text for word in ['weekly', 'brief', 'roundup', '周报', '深度']):
        return '📊 周报/深度'
    else:
        return '🧠 模型/技术'

def is_encyclopedia_article(title, summary, url):
    """判断是否为百科类文章"""
    text = (title + ' ' + summary).lower()
    return any(keyword in url.lower() for keyword in ['britannica', 'wikipedia', 'definition']) or \
           any(keyword in text for keyword in ['refers to', 'is defined as', '是指', '定义为'])

def generate_daily_insight(news_items):
    """生成今日一句话判断"""
    from ollama import chat
    try:
        titles = '\n'.join([f"{i+1}. {item['title']}" for i, item in enumerate(news_items[:3])])
        response = chat(
            model='mistral-nemo:latest',
            messages=[{'role': 'user', 'content': f'基于以下3条AI新闻标题，用一句话(20-30字)总结今日AI行业的核心趋势或要点:\n{titles}\n\n要求：简洁、有洞察力、突出最重要的信号'}]
        )
        insight = response['message']['content'].strip()
        return truncate_text(insight, 50)
    except:
        return "AI行业持续快速发展，多个领域取得重要进展。"

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

    # 分离百科类文章和正常文章
    encyclopedia_items = []
    main_items = []
    for item in news_items:
        if is_encyclopedia_article(item['title'], item['summary'], item['url']):
            encyclopedia_items.append(item)
        else:
            main_items.append(item)

    # 生成今日一句话判断
    daily_insight = generate_daily_insight(main_items[:3])

    # 构建文章列表元素
    elements = [
        # 首图
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
        {"tag": "hr"},
        {"tag": "div", "text": {"tag": "plain_text", "content": f"今日精选 {len(main_items)} 条AI行业重要资讯"}},
        {"tag": "div", "text": {"tag": "plain_text", "content": f"🧠 今日AI要点：{daily_insight}"}}
    ]

    # 添加标题摘要列表
    title_list = []
    for item in main_items:
        title = truncate_text(clean_title(item['title']), 80)
        category = get_topic_emoji(item['title'], item['summary'])
        title_list.append(f"• {category} | {title}")

    elements.append({
        "tag": "div",
        "text": {"tag": "plain_text", "content": "\n".join(title_list)}
    })
    elements.append({"tag": "hr"})

    # 添加每篇文章
    for idx, item in enumerate(main_items, 1):
        title = truncate_text(clean_title(item['title']), 80)
        summary = truncate_text(item['summary'], 150)
        source = extract_source(item['url'])
        category = get_topic_emoji(item['title'], item['summary'])

        # 第一条加焦点标识
        if idx == 1:
            title_display = f"🔥 今日焦点｜{title}"
        else:
            title_display = title

        # 文章标题和摘要合并
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**{category} | {title_display}**\n{summary}"}
        })
        # 来源和按钮
        elements.append({
            "tag": "action",
            "actions": [
                {"tag": "button", "text": {"tag": "plain_text", "content": f"阅读原文 · {source}"}, "type": "default", "url": item['url']}
            ]
        })
        # 分隔线(最后一篇不加)
        if idx < len(main_items):
            elements.append({"tag": "hr"})

    # 添加延伸阅读区
    if encyclopedia_items:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "text": {"tag": "plain_text", "content": "📎 延伸阅读"}
        })
        for item in encyclopedia_items:
            title = truncate_text(clean_title(item['title']), 60)
            source = extract_source(item['url'])
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"[{title}]({item['url']}) · {source}"}
            })

    # 单个卡片包含所有内容
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": f"🤖 AI资讯日报 | {date}"}, "template": "blue"},
            "elements": elements
        }
    }

    resp = requests.post(FEISHU_WEBHOOK_URL, json=card)
    print(f"发送卡片: {resp.status_code}")
    return resp.status_code == 200

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
