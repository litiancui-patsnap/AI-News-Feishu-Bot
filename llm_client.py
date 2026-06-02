from functools import lru_cache
import time
from typing import Optional

from config import (
    LLM_OLLAMA_FALLBACK,
    LLM_PROVIDER,
    LLM_RETRY_ATTEMPTS,
    LLM_RETRY_DELAY_SECONDS,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_CODING_MODEL,
    OPENAI_FALLBACK_MODEL,
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


def _openai_models_for_task(task: str) -> list[str]:
    models = [get_model_for_task(task)]
    if OPENAI_FALLBACK_MODEL and OPENAI_FALLBACK_MODEL not in models:
        models.append(OPENAI_FALLBACK_MODEL)
    return models


@lru_cache(maxsize=1)
def _get_openai_client():
    from openai import OpenAI

    return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


def _call_with_retries(label: str, call_once) -> str:
    attempts = max(1, LLM_RETRY_ATTEMPTS + 1)
    last_exc: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return call_once()
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            print(
                f"LLM 调用失败({label})，"
                f"{LLM_RETRY_DELAY_SECONDS:g} 秒后重试 {attempt}/{attempts - 1}: {exc}"
            )
            time.sleep(max(0, LLM_RETRY_DELAY_SECONDS))

    assert last_exc is not None
    raise last_exc


def _call_ollama(messages: list[dict[str, str]], temperature: Optional[float]) -> str:
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


def _call_openai_model(
    messages: list[dict[str, str]],
    *,
    model: str,
    temperature: Optional[float],
) -> str:
    response_kwargs = {
        "model": model,
        "messages": messages,
    }
    resolved_temperature = OPENAI_TEMPERATURE if temperature is None else temperature
    if resolved_temperature is not None:
        response_kwargs["temperature"] = resolved_temperature

    response = _get_openai_client().chat.completions.create(**response_kwargs)
    content = response.choices[0].message.content
    return (content or "").strip()


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
        return _call_with_retries(
            f"ollama:{_strip_provider_prefix(OLLAMA_MODEL)}",
            lambda: _call_ollama(messages, temperature),
        )

    if not OPENAI_BASE_URL or not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_BASE_URL and OPENAI_API_KEY must be configured for LiteLLM/OpenAI."
        )

    last_exc: Exception | None = None
    for model in _openai_models_for_task(task):
        try:
            return _call_with_retries(
                f"openai:{model}",
                lambda model=model: _call_openai_model(
                    messages,
                    model=model,
                    temperature=temperature,
                ),
            )
        except Exception as exc:
            last_exc = exc
            print(f"LLM 模型 {model} 调用失败，准备尝试备用路径: {exc}")

    if LLM_OLLAMA_FALLBACK:
        try:
            return _call_with_retries(
                f"ollama:{_strip_provider_prefix(OLLAMA_MODEL)}",
                lambda: _call_ollama(messages, temperature),
            )
        except Exception as exc:
            last_exc = exc
            print(f"Ollama 备用模型调用失败: {exc}")

    assert last_exc is not None
    raise last_exc
