from datetime import datetime, timezone

import ai_news_bot as bot


def test_build_search_query_replaces_stale_year():
    now = datetime(2026, 4, 9, tzinfo=timezone.utc)

    query = bot.build_search_query("绿化养护 城市绿化 2024", now=now)

    assert "2024" not in query
    assert "绿化养护" in query
    assert "城市绿化" in query


def test_split_search_queries_supports_topic_groups():
    assert bot.split_search_queries("绿化养护 | 3DGS 空间大模型") == [
        "绿化养护",
        "3DGS 空间大模型",
    ]


def test_extract_publication_date_from_html_meta():
    html = '<meta property="article:published_time" content="2026-04-08T06:30:00Z">'

    published_at = bot.extract_publication_date_from_html(html)

    assert published_at == datetime(2026, 4, 8, 6, 30, tzinfo=timezone.utc)


def test_is_evergreen_result_blocks_tracker_pages():
    assert bot.is_evergreen_result(
        "AI Model Release Tracker | Complete Timeline 2022-2026",
        "A full timeline of model launches and updates.",
        "https://example.com/ai-model-release-tracker",
    )


def test_is_fresh_publication_rejects_stale_articles():
    now = datetime(2026, 4, 9, 9, 0, tzinfo=timezone.utc)
    published_at = datetime(2026, 4, 6, 8, 59, tzinfo=timezone.utc)

    assert not bot.is_fresh_publication(
        published_at,
        now=now,
        max_age_hours=48,
    )


def test_looks_like_industry_news_filters_stock_noise():
    assert not bot.looks_like_industry_news(
        "Why Meta Platforms Stock Jumped Today",
        "Tech stocks were surging broadly on geopolitics and market optimism.",
        "https://example.com/markets/stocks/articles/meta-jumped",
    )


def test_looks_like_industry_news_accepts_green_maintenance():
    assert bot.looks_like_industry_news(
        "某市发布城市绿化养护标准",
        "新标准覆盖修剪、灌溉和病虫害防治要求。",
        "https://example.com/news/landscape-maintenance",
    )


def test_is_low_quality_title_filters_generic_headlines():
    assert bot.is_low_quality_title("Us Model")


def test_is_duplicate_event_merges_same_company_same_model_story():
    existing_items = [
        {
            "title": "Meta debuts new AI model, attempting to catch Google and OpenAI",
            "snippet": "Meta says its first model from the superintelligence lab is competitive.",
        }
    ]
    candidate = {
        "title": "Meta unveils Muse Spark, its first AI model from the Superintelligence Lab",
        "snippet": "The new Meta AI model is the first major release since hiring Alexandr Wang.",
    }

    assert bot.is_duplicate_event(candidate, existing_items)
