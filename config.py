import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_CONFIG = {
    "model": "ollama/mistral-nemo:latest",
    "base_url": "http://localhost:11434",
    "temperature": 0.7,
}

FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

# 可配置参数
MAX_NEWS_ITEMS = int(os.getenv("MAX_NEWS_ITEMS", "3"))  # 每日推送资讯数量
SEARCH_QUERY = os.getenv("SEARCH_QUERY", "AI artificial intelligence news 2026")  # 搜索关键词
PUSH_TIME = os.getenv("PUSH_TIME", "9:50")  # 定时推送时间

# 图片生成配置
ENABLE_INFOGRAPHIC = os.getenv("ENABLE_INFOGRAPHIC", "true").lower() == "true"  # 是否启用信息图生成
INFOGRAPHIC_OUTPUT_DIR = os.getenv("INFOGRAPHIC_OUTPUT_DIR", "./images/generated")  # 信息图输出目录
