from functools import lru_cache
from typing import Optional

from config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_CODING_MODEL,
    OPENAI_GENERAL_MODEL,
    OPENAI_TEMPERATURE,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
)


def _normalize_provider(provider: str) -> str:
    if provider in {"litellm", "openai"}:
        return "openai"
    if provider == "ollama":
        return "ollama"
    raise ValueError("Unsupported LLM_PROVIDER. Use litellm, openai, or ollama.")


def _strip_provider_prefix(model_name: str) -> str:
    if "/" in model_name:
        return model_name.split("/", 1)[1]
    return model_name


def get_model_for_task(task: str) -> str:
    if task in {"coding", "code", "prompt_debug"}:
        return OPENAI_CODING_MODEL
    return OPENAI_GENERAL_MODEL


@lru_cache(maxsize=1)
def _get_openai_client():
    from openai import OpenAI

    return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


def call_llm(
    user_prompt: str,
    *,
    system_prompt: Optional[str] = None,
    task: str = "general",
    temperature: Optional[float] = None,
) -> str:
    provider = _normalize_provider(LLM_PROVIDER)
    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    if provider == "ollama":
        from ollama import chat as ollama_chat

        response = ollama_chat(
            model=_strip_provider_prefix(OLLAMA_MODEL),
            messages=messages,
            options={
                "temperature": OLLAMA_TEMPERATURE
                if temperature is None
                else temperature
            },
        )
        return response["message"]["content"].strip()

    if not OPENAI_BASE_URL or not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_BASE_URL and OPENAI_API_KEY must be configured for LiteLLM/OpenAI."
        )

    response_kwargs = {
        "model": get_model_for_task(task),
        "messages": messages,
    }
    resolved_temperature = OPENAI_TEMPERATURE if temperature is None else temperature
    if resolved_temperature is not None:
        response_kwargs["temperature"] = resolved_temperature

    response = _get_openai_client().chat.completions.create(**response_kwargs)
    content = response.choices[0].message.content
    return (content or "").strip()
