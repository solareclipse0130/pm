from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent
ROOT_ENV_PATH = PROJECT_DIR / ".env"

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-pro"


class DeepSeekConfigurationError(RuntimeError):
    pass


class DeepSeekAPIError(RuntimeError):
    pass


def read_root_env_value(key: str, env_path: Path | None = None) -> str | None:
    resolved_env_path = env_path or ROOT_ENV_PATH
    if not resolved_env_path.exists():
        return None
    values = dotenv_values(resolved_env_path)
    raw = values.get(key)
    if raw is None:
        return None
    value = raw.strip()
    return value or None


def get_deepseek_api_key() -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if api_key:
        return api_key

    api_key = read_root_env_value("DEEPSEEK_API_KEY")
    if api_key:
        return api_key

    raise DeepSeekConfigurationError(
        "DEEPSEEK_API_KEY is not configured. Set it in the project root .env."
    )


async def _post_chat_completion(
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)


async def create_chat_completion(
    messages: list[dict[str, str]],
    *,
    api_key: str | None = None,
    response_format: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> str:
    resolved_api_key = api_key or get_deepseek_api_key()
    payload: dict[str, Any] = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        # Vendor-specific knob: DeepSeek Pro returns lower-latency completions
        # when the deliberative "thinking" mode is disabled.
        "thinking": {"type": "disabled"},
        "stream": False,
    }
    if response_format:
        payload["response_format"] = response_format
    headers = {
        "Authorization": f"Bearer {resolved_api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = await _post_chat_completion(payload, headers, timeout)
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise DeepSeekAPIError(
            f"DeepSeek API returned HTTP {error.response.status_code}."
        ) from error
    except httpx.HTTPError as error:
        raise DeepSeekAPIError("DeepSeek API request failed.") from error

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise DeepSeekAPIError(
            "DeepSeek API response did not include assistant content."
        ) from error

    if not isinstance(content, str) or not content.strip():
        raise DeepSeekAPIError("DeepSeek API response was empty.")
    return content.strip()


async def run_connectivity_check() -> dict[str, str]:
    answer = await create_chat_completion(
        [
            {
                "role": "system",
                "content": "You answer simple arithmetic checks concisely.",
            },
            {"role": "user", "content": "What is 2+2? Answer with only the number."},
        ]
    )
    return {"model": DEEPSEEK_MODEL, "answer": answer}
