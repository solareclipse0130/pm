from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

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

    for line in resolved_env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.strip() != key:
            continue
        value = value.strip().strip('"').strip("'").strip()
        return value or None

    return None


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


def create_chat_completion(
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
        response = httpx.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        status_code = error.response.status_code
        raise DeepSeekAPIError(
            f"DeepSeek API returned HTTP {status_code}."
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


def run_connectivity_check() -> dict[str, str]:
    answer = create_chat_completion(
        [
            {
                "role": "system",
                "content": "You answer simple arithmetic checks concisely.",
            },
            {"role": "user", "content": "What is 2+2? Answer with only the number."},
        ]
    )
    return {"model": DEEPSEEK_MODEL, "answer": answer}
