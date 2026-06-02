import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() == "true"


def _get_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _get_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "litellm").lower()

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://192.168.106.73:4000/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_GENERAL_MODEL = os.getenv("OPENAI_GENERAL_MODEL", "gpt-5.4")
OPENAI_CODING_MODEL = os.getenv("OPENAI_CODING_MODEL", "gpt-5.4-codex")
OPENAI_TEMPERATURE = _get_float("OPENAI_TEMPERATURE", 0.2)
OPENAI_MODEL_TOKENS = _get_int("OPENAI_MODEL_TOKENS", 128000)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral-nemo:latest")
OLLAMA_TEMPERATURE = _get_float("OLLAMA_TEMPERATURE", 0.7)
OLLAMA_MODEL_TOKENS = _get_int("OLLAMA_MODEL_TOKENS", 128000)

OPENAI_CONFIG = {
    "model": f"openai/{OPENAI_GENERAL_MODEL}",
    "api_key": OPENAI_API_KEY,
    "base_url": OPENAI_BASE_URL,
    "temperature": OPENAI_TEMPERATURE,
    "model_tokens": OPENAI_MODEL_TOKENS,
}

OLLAMA_CONFIG = {
    "model": f"ollama/{OLLAMA_MODEL}",
    "base_url": OLLAMA_BASE_URL,
    "temperature": OLLAMA_TEMPERATURE,
    "model_tokens": OLLAMA_MODEL_TOKENS,
}

FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

# Runtime options
MAX_NEWS_ITEMS = _get_int("MAX_NEWS_ITEMS", 3)
SEARCH_QUERY = os.getenv(
    "SEARCH_QUERY",
    (
        "绿化养护 | 园林绿化 | 城市绿化 | 市政养护 绿化 | "
        "养护标准 绿化 | 绿化招标 | 智慧园林 | 智能灌溉 | 园林机械 | "
        "3DGS Gaussian Splatting | 3D Gaussian Splatting 空间 | GIS 空间 | "
        "空间大模型 | 数字孪生 三维重建"
    ),
)
SEARCH_REGION = os.getenv("SEARCH_REGION", "cn-zh")
SEARCH_TIME_LIMIT = os.getenv("SEARCH_TIME_LIMIT", "w")
NEWS_MAX_AGE_HOURS = _get_int("NEWS_MAX_AGE_HOURS", 48)
PUSH_TIME = os.getenv("PUSH_TIME", "9:50")

# Infographic generation
ENABLE_INFOGRAPHIC = _get_bool("ENABLE_INFOGRAPHIC", False)
INFOGRAPHIC_OUTPUT_DIR = os.getenv(
    "INFOGRAPHIC_OUTPUT_DIR",
    "./images/generated",
)


@lru_cache(maxsize=1)
def _get_openai_scrapegraph_model():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=OPENAI_GENERAL_MODEL,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        temperature=OPENAI_TEMPERATURE,
    )


@lru_cache(maxsize=1)
def _get_ollama_scrapegraph_model():
    from langchain_community.chat_models import ChatOllama

    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=OLLAMA_TEMPERATURE,
    )


def get_active_scrapegraph_llm_config() -> dict:
    """Return the ScrapeGraphAI LLM config selected by LLM_PROVIDER."""
    if LLM_PROVIDER in {"litellm", "openai"}:
        return {
            "model_instance": _get_openai_scrapegraph_model(),
            "model_tokens": OPENAI_MODEL_TOKENS,
        }
    if LLM_PROVIDER == "ollama":
        return {
            "model_instance": _get_ollama_scrapegraph_model(),
            "model_tokens": OLLAMA_MODEL_TOKENS,
        }
    raise ValueError(
        "Unsupported LLM_PROVIDER. Use one of: litellm, openai, ollama."
    )
