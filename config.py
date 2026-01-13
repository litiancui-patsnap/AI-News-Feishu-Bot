import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_CONFIG = {
    "model": "ollama/mistral-nemo:latest",
    "base_url": "http://localhost:11434",
    "temperature": 0.7,
}

FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")
