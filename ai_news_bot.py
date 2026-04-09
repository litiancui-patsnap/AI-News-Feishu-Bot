from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import io
import json
import os
import re
import sys
import time
from typing import Any

import requests
from ddgs import DDGS

from config import (
    ENABLE_INFOGRAPHIC,
    FEISHU_APP_ID,
    FEISHU_APP_SECRET,
    FEISHU_WEBHOOK_URL,
    INFOGRAPHIC_OUTPUT_DIR,
    MAX_NEWS_ITEMS,
    NEWS_MAX_AGE_HOURS,
    SEARCH_QUERY,
    SEARCH_REGION,
    SEARCH_TIME_LIMIT,
)
from generate_news_infographic import generate_infographic_for_news
from llm_client import call_llm

SKIP_ARTICLE = "SKIP_ARTICLE"
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
NON_NEWS_PATTERNS = (
    "timeline",
    "tracker",
    "release tracker",
    "model release tracker",
    "history of",
    "retrospective",
    "roundup",
    "weekly recap",
    "weekly round-up",
    "explainer",
    "explained",
    "what is ",
    "glossary",
    "definition",
    "beginner guide",
    "tutorial",
    "complete guide",
)
EXCLUDED_URL_PATTERNS = (
    "/category/",
    "/tag/",
    "/tags/",
    "/topics/",
    "/author/",
    "/page/",
    "/archive/",
    "/search?",
    "?page=",
)
DATE_META_KEYS = (
    "article:publishedtime",
    "og:publishedtime",
    "datepublished",
    "datecreated",
    "pubdate",
    "publishdate",
    "publish-date",
    "article:modifiedtime",
    "og:updatedtime",
    "datemodified",
    "date",
)
JSON_LD_DATE_KEYS = (
    "datePublished",
    "dateCreated",
    "dateModified",
    "uploadDate",
    "date",
)
ARTICLE_BODY_JSON_KEYS = ("articleBody", "text", "description")
AI_SIGNAL_PATTERNS = (
    " ai ",
    "artificial intelligence",
    "model",
    "llm",
    "gpt",
    "gemini",
    "claude",
    "llama",
    "chatgpt",
    "copilot",
    "agent",
    "inference",
    "multimodal",
    "superintelligence",
    "chip",
    "gpu",
    "tpu",
    "semiconductor",
    "openai",
    "anthropic",
    "deepmind",
    "muse spark",
)
MARKET_NOISE_PATTERNS = (
    "stock jumped",
    "shares jumped",
    "shares rose",
    "share price",
    "nasdaq",
    "s&p 500",
    "price target",
    "dividend",
)
PARAGRAPH_NOISE_PATTERNS = (
    "subscribe",
    "sign up",
    "newsletter",
    "advertisement",
    "all rights reserved",
    "cookie",
    "privacy policy",
    "terms of service",
)
EVENT_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "after",
    "amid",
    "into",
    "over",
    "will",
    "would",
    "could",
    "their",
    "about",
    "mark",
    "ceo",
    "today",
    "latest",
    "first",
    "new",
    "its",
    "his",
    "her",
    "they",
    "them",
    "attempting",
    "spending",
    "billions",
    "says",
    "said",
}
COMPANY_ALIASES = {
    "openai": ("openai", "chatgpt", "gpt"),
    "google": ("google", "gemini", "deepmind", "alphabet"),
    "meta": ("meta", "facebook", "instagram", "whatsapp"),
    "anthropic": ("anthropic", "claude"),
    "microsoft": ("microsoft", "copilot"),
    "amazon": ("amazon", "aws"),
    "nvidia": ("nvidia",),
    "apple": ("apple", "siri"),
    "xai": ("xai", "grok"),
}
MAX_ITEMS_PER_COMPANY = 2


def _now_utc(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _dedupe_tokens(text: str) -> str:
    seen: set[str] = set()
    ordered_tokens: list[str] = []
    for token in text.split():
        token_key = token.lower()
        if token_key in seen:
            continue
        seen.add(token_key)
        ordered_tokens.append(token)
    return " ".join(ordered_tokens)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _event_text(*parts: str) -> str:
    return _normalize_text(" ".join(part for part in parts if part))


def extract_company_tags(text: str) -> set[str]:
    lowered = text.lower()
    matches: set[str] = set()
    for company, aliases in COMPANY_ALIASES.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", lowered) for alias in aliases):
            matches.add(company)
    return matches


def extract_event_tokens(*parts: str) -> set[str]:
    text = _event_text(*parts).lower()
    tokens = set(re.findall(r"[a-z0-9][a-z0-9.+-]{2,}", text))
    return {
        token
        for token in tokens
        if token not in EVENT_STOPWORDS and not token.isdigit()
    }


def looks_like_ai_news(title: str, summary: str, url: str) -> bool:
    text = f" {title.lower()} {summary.lower()} {url.lower()} "
    if any(pattern in text for pattern in MARKET_NOISE_PATTERNS) and not any(
        pattern in text for pattern in AI_SIGNAL_PATTERNS
    ):
        return False
    return any(pattern in text for pattern in AI_SIGNAL_PATTERNS)


def is_low_quality_title(title: str) -> bool:
    normalized = clean_title(title)
    tokens = re.findall(r"[a-zA-Z0-9]+", normalized.lower())
    if not tokens:
        return True
    if len(tokens) <= 2:
        return True
    if len(tokens) <= 4 and not extract_company_tags(normalized) and "ai" not in normalized.lower():
        return True
    return False


def is_duplicate_event(
    candidate: dict[str, str],
    existing_items: list[dict[str, str]],
) -> bool:
    candidate_text = _event_text(
        candidate.get("title", ""),
        candidate.get("summary", ""),
        candidate.get("snippet", ""),
    )
    candidate_tokens = extract_event_tokens(candidate_text)
    candidate_companies = extract_company_tags(candidate_text)

    for existing in existing_items:
        existing_text = _event_text(
            existing.get("title", ""),
            existing.get("summary", ""),
            existing.get("snippet", ""),
        )
        existing_tokens = extract_event_tokens(existing_text)
        existing_companies = extract_company_tags(existing_text)
        overlap = candidate_tokens & existing_tokens
        if candidate_companies & existing_companies and len(overlap) >= 3:
            return True
        if len(overlap) >= 5:
            return True
    return False


def exceeds_company_limit(
    candidate: dict[str, str],
    accepted_items: list[dict[str, str]],
) -> bool:
    candidate_companies = extract_company_tags(
        _event_text(candidate.get("title", ""), candidate.get("summary", ""), candidate.get("snippet", ""))
    )
    if not candidate_companies:
        return False

    company_counts = {company: 0 for company in candidate_companies}
    for item in accepted_items:
        item_companies = extract_company_tags(
            _event_text(item.get("title", ""), item.get("summary", ""), item.get("snippet", ""))
        )
        for company in candidate_companies & item_companies:
            company_counts[company] += 1

    return any(count >= MAX_ITEMS_PER_COMPANY for count in company_counts.values())


def build_search_query(base_query: str, now: datetime | None = None) -> str:
    """Normalize the search query so it always targets the current month and year."""
    now = now or datetime.now()
    cleaned = re.sub(r"\b20\d{2}\b", " ", base_query)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    suffix = f"{now.strftime('%B')} {now.year}"
    return _dedupe_tokens(f"{cleaned} {suffix}".strip())


def parse_datetime_candidate(
    value: Any,
    *,
    now: datetime | None = None,
) -> datetime | None:
    """Parse publication dates from ISO strings, RFC822 strings, or relative labels."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return _normalize_datetime(value)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)

    text = str(value).strip()
    if not text:
        return None

    now_utc = _now_utc(now)
    lowered = text.lower()
    if lowered in {"today", "just now"}:
        return now_utc
    if lowered == "yesterday":
        return now_utc - timedelta(days=1)

    relative_match = re.fullmatch(
        r"(?P<count>\d+)\s+(?P<unit>minute|hour|day|week)s?\s+ago",
        lowered,
    )
    if relative_match:
        count = int(relative_match.group("count"))
        unit = relative_match.group("unit")
        delta_map = {
            "minute": timedelta(minutes=count),
            "hour": timedelta(hours=count),
            "day": timedelta(days=count),
            "week": timedelta(weeks=count),
        }
        return now_utc - delta_map[unit]

    iso_like = text.replace("Z", "+00:00")
    try:
        return _normalize_datetime(datetime.fromisoformat(iso_like))
    except ValueError:
        pass

    try:
        return _normalize_datetime(parsedate_to_datetime(text))
    except (TypeError, ValueError, IndexError, OverflowError):
        pass

    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
    ):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def extract_date_from_url(url: str) -> datetime | None:
    """Parse yyyy/mm/dd and similar patterns from article URLs."""
    for pattern in (
        r"/(\d{4})/(\d{2})/(\d{2})/",
        r"/(\d{4})-(\d{2})-(\d{2})",
        r"(\d{4})(\d{2})(\d{2})",
    ):
        match = re.search(pattern, url)
        if not match:
            continue
        try:
            year, month, day = (int(part) for part in match.groups())
            return datetime(year, month, day, tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_html_attrs(tag: str) -> dict[str, str]:
    return {
        key.lower(): value
        for key, value in re.findall(r'([:\w-]+)\s*=\s*["\']([^"\']*)["\']', tag)
    }


def _normalize_meta_key(key: str) -> str:
    return re.sub(r"[^a-z:]", "", key.lower())


def _iter_json_ld_dates(payload: Any, wanted_key: str) -> list[str]:
    if isinstance(payload, dict):
        matches: list[str] = []
        for key, value in payload.items():
            if key == wanted_key and isinstance(value, str):
                matches.append(value)
            matches.extend(_iter_json_ld_dates(value, wanted_key))
        return matches
    if isinstance(payload, list):
        matches: list[str] = []
        for item in payload:
            matches.extend(_iter_json_ld_dates(item, wanted_key))
        return matches
    return []


def extract_publication_date_from_html(
    html: str,
    *,
    now: datetime | None = None,
) -> datetime | None:
    """Extract publication dates from meta tags, time tags, and JSON-LD."""
    if not html:
        return None

    for tag in re.findall(r"<meta\b[^>]*>", html, flags=re.IGNORECASE):
        attrs = _parse_html_attrs(tag)
        raw_key = attrs.get("property") or attrs.get("name") or attrs.get("itemprop")
        if not raw_key:
            continue
        if _normalize_meta_key(raw_key) not in DATE_META_KEYS:
            continue
        parsed = parse_datetime_candidate(attrs.get("content"), now=now)
        if parsed:
            return parsed

    for tag in re.findall(r"<time\b[^>]*>", html, flags=re.IGNORECASE):
        attrs = _parse_html_attrs(tag)
        parsed = parse_datetime_candidate(attrs.get("datetime"), now=now)
        if parsed:
            return parsed

    for script_content in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        script_content = script_content.strip()
        if not script_content:
            continue
        try:
            payload = json.loads(script_content)
        except json.JSONDecodeError:
            continue

        for key in JSON_LD_DATE_KEYS:
            for candidate in _iter_json_ld_dates(payload, key):
                parsed = parse_datetime_candidate(candidate, now=now)
                if parsed:
                    return parsed

    return None


def resolve_publication_date(
    url: str,
    *,
    search_result_date: str = "",
    html: str = "",
    headers: dict[str, str] | None = None,
    now: datetime | None = None,
) -> datetime | None:
    """Choose the best publication date candidate for an article."""
    candidates = [
        extract_publication_date_from_html(html, now=now),
        parse_datetime_candidate(search_result_date, now=now),
        extract_date_from_url(url),
        parse_datetime_candidate((headers or {}).get("Last-Modified"), now=now),
    ]
    for candidate in candidates:
        if candidate:
            return candidate
    return None


def is_fresh_publication(
    published_at: datetime,
    *,
    now: datetime | None = None,
    max_age_hours: int = NEWS_MAX_AGE_HOURS,
) -> bool:
    now_utc = _now_utc(now)
    published_utc = _normalize_datetime(published_at)
    if published_utc > now_utc + timedelta(hours=6):
        return False
    return published_utc >= now_utc - timedelta(hours=max_age_hours)


def is_candidate_article_url(url: str) -> bool:
    lowered = url.lower()
    return not any(pattern in lowered for pattern in EXCLUDED_URL_PATTERNS)


def is_evergreen_result(title: str, summary: str, url: str) -> bool:
    text = " ".join([title, summary, url]).lower()
    return any(pattern in text for pattern in NON_NEWS_PATTERNS)


def fetch_publication_context(url: str) -> tuple[str, dict[str, str]]:
    try:
        response = requests.get(
            url,
            headers=HTTP_HEADERS,
            timeout=10,
            allow_redirects=True,
        )
        if response.status_code >= 400:
            return "", {}

        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type.lower():
            return "", dict(response.headers)

        return response.text[:500000], dict(response.headers)
    except requests.RequestException:
        return "", {}


def validate_news_result(
    raw_result: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, str] | None:
    title = raw_result.get("title", "").strip()
    url = raw_result.get("url") or raw_result.get("href") or ""
    summary = raw_result.get("body") or raw_result.get("snippet") or ""
    source = raw_result.get("source", "")

    if not title or not url:
        return None
    if not is_candidate_article_url(url):
        print(f"跳过非文章页: {url}")
        return None
    if is_low_quality_title(title):
        print(f"跳过低质量标题结果: {title}")
        return None
    if not looks_like_ai_news(title, summary, url):
        print(f"跳过低相关度结果: {title}")
        return None
    if is_evergreen_result(title, summary, url):
        print(f"跳过汇总/百科类结果: {title}")
        return None

    html, headers = fetch_publication_context(url)
    published_at = resolve_publication_date(
        url,
        search_result_date=raw_result.get("date", ""),
        html=html,
        headers=headers,
        now=now,
    )
    if not published_at:
        print(f"跳过未标明发布时间的结果: {title}")
        return None
    if not is_fresh_publication(published_at, now=now):
        print(f"跳过过旧结果: {title} ({published_at.date()})")
        return None

    return {
        "title": title,
        "url": url,
        "snippet": summary.strip(),
        "source": source.strip(),
        "published_at": _normalize_datetime(published_at).isoformat(),
    }


def search_ai_news(query: str = SEARCH_QUERY, max_results: int = 5) -> list[dict[str, str]]:
    """Use DDGS news search and strict freshness validation to collect recent AI news."""
    resolved_query = build_search_query(query)
    print(f"搜索查询: {resolved_query}")

    results: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    try:
        ddgs = DDGS()
        raw_results = ddgs.news(
            resolved_query,
            region=SEARCH_REGION,
            timelimit=SEARCH_TIME_LIMIT,
            max_results=max_results * 10,
        )
        for raw_result in raw_results:
            candidate = validate_news_result(raw_result)
            if not candidate:
                continue

            url = candidate["url"]
            if url in seen_urls:
                continue
            if is_duplicate_event(candidate, results):
                print(f"跳过重复事件: {candidate['title']}")
                continue
            if exceeds_company_limit(candidate, results):
                print(f"跳过公司过度集中结果: {candidate['title']}")
                continue

            seen_urls.add(url)
            results.append(candidate)
            if len(results) >= max_results:
                break
            time.sleep(0.2)
    except Exception as exc:
        print(f"搜索出错: {exc}")

    results.sort(key=lambda item: item["published_at"], reverse=True)
    return results


def truncate_text(text: str, max_len: int) -> str:
    """智能截断文本，在标点符号处截断。"""
    if len(text) <= max_len:
        return text

    truncated = text[:max_len]
    for punct in ["。", "！", "？", ".", "!", "?", "，", ","]:
        last_punct = truncated.rfind(punct)
        if last_punct > max_len * 0.6:
            return truncated[: last_punct + 1]
    return truncated + "..."


def translate_to_chinese(text: str) -> str:
    """Translate or summarize English snippets into concise Chinese."""
    if not text.strip():
        return ""

    try:
        return call_llm(
            (
                "请把下面这段 AI 新闻片段整理成中文摘要。\n"
                "要求：\n"
                "1. 只根据输入内容改写，不补充未出现的日期、数字或事实\n"
                "2. 优先保留公司名、产品名、明确日期与关键动作\n"
                "3. 输出 2 句话以内，总字数不超过 120 字\n"
                f"新闻片段：\n{text}"
            ),
            system_prompt=(
                "你是一名科技新闻编辑，只做客观压缩，不脑补背景，不延展评论。"
            ),
            task="translation",
        )
    except Exception as exc:
        print(f"翻译失败: {exc}")
        return text


def _extract_json_ld_texts(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        matches: list[str] = []
        for key, value in payload.items():
            if key in ARTICLE_BODY_JSON_KEYS and isinstance(value, str):
                matches.append(value)
            matches.extend(_extract_json_ld_texts(value))
        return matches
    if isinstance(payload, list):
        matches: list[str] = []
        for item in payload:
            matches.extend(_extract_json_ld_texts(item))
        return matches
    return []


def _html_fragment_to_text(fragment: str) -> str:
    text = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    text = re.sub(r"(?i)</(p|div|li|section|article|h1|h2|h3|h4|h5|h6)>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return _normalize_text(unescape(text))


def extract_article_text_from_html(html: str) -> str:
    if not html:
        return ""

    cleaned_html = re.sub(
        r"(?is)<(script|style|noscript|svg|iframe|footer|header|nav|form|aside)[^>]*>.*?</\1>",
        " ",
        html,
    )
    candidates: list[str] = []

    for script_content in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        cleaned_html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        script_content = script_content.strip()
        if not script_content:
            continue
        try:
            payload = json.loads(script_content)
        except json.JSONDecodeError:
            continue
        for value in _extract_json_ld_texts(payload):
            normalized = _normalize_text(unescape(value))
            if len(normalized) >= 300:
                candidates.append(normalized)

    article_match = re.search(
        r"(?is)<article\b[^>]*>(.*?)</article>",
        cleaned_html,
    )
    article_html = article_match.group(1) if article_match else cleaned_html

    paragraphs: list[str] = []
    for fragment in re.findall(r"(?is)<p\b[^>]*>(.*?)</p>", article_html):
        paragraph = _html_fragment_to_text(fragment)
        if len(paragraph) < 60:
            continue
        if any(pattern in paragraph.lower() for pattern in PARAGRAPH_NOISE_PATTERNS):
            continue
        paragraphs.append(paragraph)

    if len(paragraphs) >= 3:
        candidates.append("\n".join(paragraphs[:15]))
    elif paragraphs:
        candidates.append("\n".join(paragraphs))

    fallback_text = _html_fragment_to_text(article_html)
    if len(fallback_text) >= 500:
        candidates.append(fallback_text[:12000])

    if not candidates:
        return ""
    return max(candidates, key=len)[:12000]


def scrape_article_content(
    url: str,
    *,
    snippet: str = "",
    published_at: str = "",
) -> Any:
    """Fetch article HTML with requests and summarize extracted body text."""
    html, _headers = fetch_publication_context(url)
    article_text = extract_article_text_from_html(html)
    if len(article_text) < 500:
        raise ValueError("无法从 HTML 提取足够正文")

    published_label = format_published_date(published_at)
    cutoff_date = (
        datetime.now(timezone.utc) - timedelta(hours=NEWS_MAX_AGE_HOURS)
    ).strftime("%Y-%m-%d")
    return call_llm(
        f"""你正在为今天的 AI 日报提取新闻摘要。以下页面已经通过发布时间校验：

页面链接：{url}
发布时间：{published_label}
搜索摘要：{snippet}

如果正文属于以下任一情况，请只返回 {SKIP_ARTICLE}：
1. 时间线、Tracker、汇总、周报、百科、教程、产品文档或历史回顾
2. 页面主体不是单篇新闻，而是列表页、专题页、资料页
3. 正文找不到明确的新闻事件，或者主要在回顾 {cutoff_date} 之前的旧事件

如果页面符合要求，请输出中文摘要，并严格遵守：
1. 首句必须写清楚谁在什么日期做了什么
2. 保留文章中的明确日期、关键数字、公司名、产品名
3. 不要使用“最近”“近期”“日前”等模糊时间词
4. 不要写背景铺垫、评论性空话、行业常识
5. 2-3 句话，总字数不超过 150 字
6. 只输出摘要正文或 {SKIP_ARTICLE}，不要额外解释

正文内容：
{article_text}""",
        system_prompt="你是一名科技新闻编辑，只根据给定正文提炼高密度中文摘要。",
        task="general",
    )


def extract_summary_text(content: Any, fallback: str = "") -> str:
    if isinstance(content, dict):
        for key in ("summary", "content", "answer", "result"):
            value = content.get(key)
            if value:
                return str(value).strip()
    if content is None:
        return fallback.strip()
    return str(content).strip()


def is_skip_article_response(text: str) -> bool:
    normalized = text.strip().upper()
    return normalized == SKIP_ARTICLE or normalized.startswith(f"{SKIP_ARTICLE}:")


def clean_title(title: str) -> str:
    """清理标题，移除网站名称后缀。"""
    patterns = [r"\s*[|\-–—]\s*[A-Za-z\s]+$", r"\s*\|\s*.+$"]
    for pattern in patterns:
        title = re.sub(pattern, "", title)
    return title.strip()


def extract_source(url: str) -> str:
    """从 URL 提取来源网站名称。"""
    from urllib.parse import urlparse

    domain = urlparse(url).netloc
    domain = domain.replace("www.", "").split(".")[0]
    return domain.capitalize()


def format_published_date(value: str) -> str:
    parsed = parse_datetime_candidate(value)
    if not parsed:
        return "日期待确认"
    return parsed.astimezone().strftime("%Y-%m-%d")


def get_topic_emoji(title: str, summary: str) -> str:
    """根据标题和摘要推断主题分类标签。"""
    text = (title + " " + summary).lower()

    if any(
        word in text
        for word in ["chip", "gpu", "nvidia", "amd", "芯片", "硬件", "hardware"]
    ):
        return "🖥️ 芯片/硬件"
    if any(
        word in text
        for word in ["regulation", "policy", "law", "监管", "法规", "政策", "伦理"]
    ):
        return "📜 政策/伦理"
    if any(
        word in text
        for word in [
            "funding",
            "investment",
            "acquisition",
            "company",
            "融资",
            "投资",
            "收购",
            "公司",
            "产业",
        ]
    ):
        return "🏭 产业/公司"
    if any(word in text for word in ["weekly", "brief", "roundup", "周报", "深度"]):
        return "📊 周报/深度"
    return "🧠 模型/技术"


def is_encyclopedia_article(title: str, summary: str, url: str) -> bool:
    """判断是否为百科类文章。"""
    text = (title + " " + summary).lower()
    return any(
        keyword in url.lower()
        for keyword in ["britannica", "wikipedia", "definition"]
    ) or any(
        keyword in text for keyword in ["refers to", "is defined as", "是指", "定义为"]
    )


def generate_daily_insight(news_items: list[dict[str, str]]) -> str:
    """Generate a concise Chinese daily insight using fresh news only."""
    try:
        today = datetime.now().strftime("%Y年%m月%d日")
        news_details = "\n".join(
            [
                (
                    f"{i + 1}. 标题：{item['title']}\n"
                    f"   发布时间：{format_published_date(item.get('published_at', ''))}\n"
                    f"   摘要：{item.get('summary', '')[:100]}"
                )
                for i, item in enumerate(news_items[:3])
            ]
        )

        insight = call_llm(
            f"""今天是{today}。以下资讯都已经通过发布时间校验，请基于它们生成一句日报洞察：

{news_details}

要求：
1. 必须点名具体公司、技术或事件，不要泛泛而谈
2. 必须体现今天这批新闻最特殊的共同信号
3. 20-35 字，简洁有力
4. 避免使用“持续”“不断”“进一步”等模糊词
5. 只输出一句话，不要解释""",
            system_prompt="你是一名中文科技编辑，只写一句信息密度高的日报判断。",
            task="insight",
        ).strip()
        insight = insight.replace('"', "").replace("“", "").replace("”", "").strip("。！？")
        return truncate_text(insight, 50)
    except Exception as exc:
        print(f"生成今日洞察失败: {exc}")
        return "近两日 AI 新闻集中在模型发布、产品落地和基础设施竞争。"


def get_tenant_access_token() -> str | None:
    """获取飞书 tenant_access_token。"""
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        return None

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET,
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        result = response.json()
        if result.get("code") == 0:
            return result.get("tenant_access_token")
        print(f"获取 token 失败: {result.get('msg')}")
    except Exception as exc:
        print(f"获取 token 异常: {exc}")
    return None


def upload_image_to_feishu(image_path: str) -> str | None:
    """上传图片到飞书并返回 image_key。"""
    token = get_tenant_access_token()
    if not token:
        print("无法获取飞书访问令牌，跳过图片上传")
        return None

    if not os.path.exists(image_path):
        print(f"图片文件不存在: {image_path}")
        return None

    url = "https://open.feishu.cn/open-apis/im/v1/images"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with open(image_path, "rb") as file_handle:
            files = {"image": (os.path.basename(image_path), file_handle, "image/png")}
            data = {"image_type": "message"}
            response = requests.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=20,
            )
            result = response.json()

        if result.get("code") == 0:
            image_key = result.get("data", {}).get("image_key")
            print(f"图片上传成功: {image_key}")
            return image_key
        print(f"图片上传失败: {result.get('msg')}")
    except Exception as exc:
        print(f"图片上传异常: {exc}")
    return None


def send_to_feishu(news_items: list[dict[str, str]]) -> bool:
    """发送卡片消息到飞书。"""
    if not news_items:
        print("没有通过时效校验的新内容，今日不发送日报。")
        return False

    date = datetime.now().strftime("%Y/%m/%d")

    encyclopedia_items: list[dict[str, str]] = []
    main_items: list[dict[str, str]] = []
    for item in news_items:
        if is_encyclopedia_article(item["title"], item["summary"], item["url"]):
            encyclopedia_items.append(item)
        else:
            main_items.append(item)

    if not main_items:
        print("没有可发送的单篇近期新闻，今日不发送日报。")
        return False

    daily_insight = generate_daily_insight(main_items[:3])

    image_key = None
    if ENABLE_INFOGRAPHIC:
        focus_news = dict(main_items[0])
        focus_news["category"] = get_topic_emoji(
            focus_news["title"],
            focus_news["summary"],
        )

        print("正在为今日焦点生成信息图...")
        try:
            infographic_path = generate_infographic_for_news(
                focus_news,
                INFOGRAPHIC_OUTPUT_DIR,
            )
            if infographic_path and os.path.exists(infographic_path):
                print(f"信息图生成成功: {infographic_path}")
                image_key = upload_image_to_feishu(infographic_path)
            else:
                print("信息图生成失败，使用默认首图")
                banner_path = os.path.join(
                    os.path.dirname(__file__),
                    "images",
                    "ai_banner.png",
                )
                image_key = upload_image_to_feishu(banner_path)
        except Exception as exc:
            print(f"生成信息图时出错: {exc}，使用默认首图")
            banner_path = os.path.join(
                os.path.dirname(__file__),
                "images",
                "ai_banner.png",
            )
            image_key = upload_image_to_feishu(banner_path)
    else:
        print("信息图生成已禁用，使用默认首图")
        banner_path = os.path.join(os.path.dirname(__file__), "images", "ai_banner.png")
        image_key = upload_image_to_feishu(banner_path)

    elements: list[dict[str, Any]] = []
    if image_key:
        elements.append(
            {
                "tag": "img",
                "img_key": image_key,
                "alt": {"tag": "plain_text", "content": "AI资讯日报"},
                "mode": "compact_horizontal",
                "preview": True,
            }
        )

    elements.append(
        {
            "tag": "div",
            "text": {
                "tag": "plain_text",
                "content": (
                    f"今日精选 {len(main_items)} 条过去 {NEWS_MAX_AGE_HOURS} 小时内的 AI 资讯\n"
                    f"🧠 今日AI要点：{daily_insight}"
                ),
            },
        }
    )

    title_list = []
    for item in main_items:
        title = truncate_text(clean_title(item["title"]), 80)
        category = get_topic_emoji(item["title"], item["summary"])
        published_label = format_published_date(item.get("published_at", ""))
        title_list.append(f"• {category} | {published_label} | {title}")

    elements.append(
        {
            "tag": "div",
            "text": {"tag": "plain_text", "content": "\n".join(title_list)},
        }
    )
    elements.append({"tag": "hr"})

    for index, item in enumerate(main_items, start=1):
        title = truncate_text(clean_title(item["title"]), 80)
        summary = truncate_text(item["summary"], 150)
        source = item.get("source") or extract_source(item["url"])
        category = get_topic_emoji(item["title"], item["summary"])
        published_label = format_published_date(item.get("published_at", ""))
        title_display = f"🔥 今日焦点｜{title}" if index == 1 else title

        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**{category} | {title_display}**  "
                        f"[阅读原文 · {source} · {published_label}]({item['url']})\n"
                        f"{summary}"
                    ),
                },
            }
        )
        if index < len(main_items):
            elements.append({"tag": "hr"})

    if encyclopedia_items:
        elements.append({"tag": "hr"})
        elements.append(
            {
                "tag": "div",
                "text": {"tag": "plain_text", "content": "📎 延伸阅读"},
            }
        )
        for item in encyclopedia_items:
            title = truncate_text(clean_title(item["title"]), 60)
            source = item.get("source") or extract_source(item["url"])
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"[{title}]({item['url']}) · {source}",
                    },
                }
            )

    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "lark_md",
                    "content": f"AI资讯日报 | <font color='orange'>{date}</font>",
                },
                "template": "blue",
                "ud_icon": {
                    "tag": "img",
                    "img_key": "img_v3_02u7_3dfb2d58-1885-400f-9278-4c049e5d908g",
                },
            },
            "elements": elements,
        },
    }

    if not FEISHU_WEBHOOK_URL:
        print("未配置 FEISHU_WEBHOOK_URL，跳过发送。")
        return False

    try:
        response = requests.post(FEISHU_WEBHOOK_URL, json=card, timeout=20)
        print(f"发送卡片: {response.status_code}")
        return response.status_code == 200
    except Exception as exc:
        print(f"发送飞书卡片异常: {exc}")
        return False


def main() -> bool:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("搜索最新 AI 资讯...")
    search_results = search_ai_news(SEARCH_QUERY, max_results=MAX_NEWS_ITEMS)
    if not search_results:
        print("未找到通过发布时间校验的新内容，今日不发送日报。")
        return False

    news_items: list[dict[str, str]] = []
    seen_titles: set[str] = set()

    for result in search_results:
        title = result["title"]
        normalized_title = clean_title(title).lower()
        if normalized_title in seen_titles:
            print(f"\n跳过重复标题: {title}")
            continue
        if is_duplicate_event(result, news_items):
            print(f"\n跳过主流程重复事件: {title}")
            continue
        if exceeds_company_limit(result, news_items):
            print(f"\n跳过主流程公司过度集中结果: {title}")
            continue

        seen_titles.add(normalized_title)
        print(
            f"\n处理第 {len(news_items) + 1} 条: "
            f"{title} ({format_published_date(result['published_at'])})"
        )

        try:
            content = scrape_article_content(
                result["url"],
                snippet=result.get("snippet", ""),
                published_at=result.get("published_at", ""),
            )
            summary = extract_summary_text(content, fallback=result["snippet"])
            if is_skip_article_response(summary):
                print("抓取结果判定为非单篇近期新闻，跳过")
                continue
        except Exception as exc:
            print(f"抓取失败: {exc}，使用翻译备用方案")
            summary = translate_to_chinese(result["snippet"][:300])

        summary = truncate_text(summary.strip(), 200)
        if not summary:
            print("摘要为空，跳过")
            continue
        if is_skip_article_response(summary):
            print("备用摘要仍判定为非单篇近期新闻，跳过")
            continue

        news_items.append(
            {
                "title": title,
                "url": result["url"],
                "summary": summary,
                "snippet": result.get("snippet", ""),
                "published_at": result["published_at"],
                "source": result.get("source", ""),
            }
        )

    print(f"\n共获取 {len(news_items)} 条通过时效校验的资讯")
    if not news_items:
        print("没有可发送的新内容，今日不发送日报。")
        return False

    print("\n发送到飞书...")
    if send_to_feishu(news_items):
        print("发送成功!")
        return True

    print("发送失败")
    return False


if __name__ == "__main__":
    main()
