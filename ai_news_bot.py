from scrapegraphai.graphs import SmartScraperGraph
from ddgs import DDGS
from config import OLLAMA_CONFIG, FEISHU_WEBHOOK_URL, FEISHU_APP_ID, FEISHU_APP_SECRET, MAX_NEWS_ITEMS, SEARCH_QUERY, ENABLE_INFOGRAPHIC, INFOGRAPHIC_OUTPUT_DIR
import requests
import time
from datetime import datetime
import os
from generate_news_infographic import generate_infographic_for_news

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
        prompt="""请用中文生成一段精准的AI资讯摘要，要求：

1. 核心信息提取：
   - 明确指出"谁"（公司/机构/人物）
   - 明确说明"做了什么"（具体行动/发布/决策）
   - 明确时间（如果文章提到具体日期，必须包含）
   - 关键数据（性能提升百分比、融资金额、用户数等）

2. 避免模糊表述：
   - 不要使用"最近"、"近期"等模糊时间词
   - 不要使用"某公司"、"该技术"等指代不明的词
   - 避免泛泛而谈的背景介绍

3. 突出新闻价值：
   - 这条新闻的独特之处是什么？
   - 与之前的类似新闻有何不同？
   - 对行业/用户的具体影响是什么？

4. 格式要求：
   - 2-3句话，每句话表达一个完整观点
   - 总字数不超过150字
   - 使用具体的名词和动词，避免形容词堆砌

示例格式：
[公司名]于[具体时间]发布[具体产品/技术]，[关键特性/数据]。该[产品/技术]主要解决[具体问题]，预计将[具体影响]。[补充信息：如价格/发布时间/适用场景等]。""",
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
    from datetime import datetime
    try:
        # 获取当前日期，增加时间上下文
        today = datetime.now().strftime("%Y年%m月%d日")

        # 构建更详细的新闻信息
        news_details = '\n'.join([
            f"{i+1}. 标题：{item['title']}\n   摘要：{item.get('summary', '')[:100]}"
            for i, item in enumerate(news_items[:3])
        ])

        response = chat(
            model='mistral-nemo:latest',
            messages=[{'role': 'user', 'content': f'''今天是{today}，请基于以下3条AI新闻，生成一句独特的行业洞察：

{news_details}

要求：
1. 必须提及具体的公司名、技术名或事件（不要泛泛而谈）
2. 突出今日新闻的独特性（与昨日不同的地方）
3. 20-35字，简洁有力
4. 避免使用"持续"、"不断"、"进一步"等模糊词
5. 体现行业趋势或重要信号

示例格式：
- [公司]推出[技术]，[领域]竞争加剧
- [技术方向]成焦点，[影响]值得关注
- [事件]标志着[趋势]，行业格局生变'''}]
        )
        insight = response['message']['content'].strip()
        # 移除引号和多余的标点
        insight = insight.replace('"', '').replace('"', '').replace('"', '').strip('。！？')
        return truncate_text(insight, 50)
    except Exception as e:
        print(f"生成今日洞察失败: {e}")
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

def get_tenant_access_token():
    """获取飞书tenant_access_token"""
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        return None

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        result = response.json()
        if result.get("code") == 0:
            return result.get("tenant_access_token")
        else:
            print(f"获取token失败: {result.get('msg')}")
            return None
    except Exception as e:
        print(f"获取token异常: {e}")
        return None

def upload_image_to_feishu(image_path):
    """上传图片到飞书并返回image_key"""
    token = get_tenant_access_token()
    if not token:
        print("无法获取飞书访问令牌，跳过图片上传")
        return None

    if not os.path.exists(image_path):
        print(f"图片文件不存在: {image_path}")
        return None

    url = "https://open.feishu.cn/open-apis/im/v1/images"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        with open(image_path, 'rb') as f:
            files = {
                'image': (os.path.basename(image_path), f, 'image/png')
            }
            data = {
                'image_type': 'message'
            }
            response = requests.post(url, headers=headers, files=files, data=data)
            result = response.json()

            if result.get("code") == 0:
                image_key = result.get("data", {}).get("image_key")
                print(f"图片上传成功: {image_key}")
                return image_key
            else:
                print(f"图片上传失败: {result.get('msg')}")
                return None
    except Exception as e:
        print(f"图片上传异常: {e}")
        return None

def send_to_feishu(news_items):
    """发送卡片消息到飞书"""
    from datetime import datetime
    date = datetime.now().strftime("%Y/%m/%d")

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

    # 为今日焦点生成信息图
    image_key = None
    if ENABLE_INFOGRAPHIC and main_items:
        focus_news = main_items[0]  # 第一条新闻
        focus_news['category'] = get_topic_emoji(focus_news['title'], focus_news['summary'])

        print("正在为今日焦点生成信息图...")
        try:
            infographic_path = generate_infographic_for_news(focus_news, INFOGRAPHIC_OUTPUT_DIR)

            if infographic_path and os.path.exists(infographic_path):
                print(f"信息图生成成功: {infographic_path}")
                image_key = upload_image_to_feishu(infographic_path)
            else:
                print("信息图生成失败，使用默认首图")
                banner_path = os.path.join(os.path.dirname(__file__), "images", "ai_banner.png")
                image_key = upload_image_to_feishu(banner_path)
        except Exception as e:
            print(f"生成信息图时出错: {e}，使用默认首图")
            banner_path = os.path.join(os.path.dirname(__file__), "images", "ai_banner.png")
            image_key = upload_image_to_feishu(banner_path)
    else:
        # 未启用信息图生成，使用默认首图
        print("信息图生成已禁用，使用默认首图")
        banner_path = os.path.join(os.path.dirname(__file__), "images", "ai_banner.png")
        image_key = upload_image_to_feishu(banner_path)

    # 构建文章列表元素
    elements = []

    # 如果成功上传图片，添加首图
    if image_key:
        elements.append({
            "tag": "img",
            "img_key": image_key,
            "alt": {
                "tag": "plain_text",
                "content": "AI资讯日报"
            },
            "mode": "compact_horizontal",  # 使用紧凑模式，高度最小
            "preview": True
        })

    # 添加摘要信息（合并为一个元素）
    elements.append({
        "tag": "div",
        "text": {
            "tag": "plain_text",
            "content": f"今日精选 {len(main_items)} 条AI行业重要资讯\n🧠 今日AI要点：{daily_insight}"
        }
    })

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

        # 文章标题、摘要和来源链接合并为一个元素
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{category} | {title_display}**  [阅读原文 · {source}]({item['url']})\n{summary}"
            }
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
            "header": {
                "title": {"tag": "lark_md", "content": f"AI资讯日报 | <font color='orange'>{date}</font>"},
                "template": "blue",
                "ud_icon": {
                    "tag": "img",
                    "img_key": "img_v3_02u7_3dfb2d58-1885-400f-9278-4c049e5d908g"
                }
            },
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
