from pathlib import Path

import httpx
import pytest

from app.deepseek import (
    DEEPSEEK_API_URL,
    DEEPSEEK_MODEL,
    DeepSeekAPIError,
    DeepSeekConfigurationError,
    create_chat_completion,
    get_deepseek_api_key,
    read_root_env_value,
)


def build_response(status_code: int, json: dict[str, object]) -> httpx.Response:
    request = httpx.Request("POST", DEEPSEEK_API_URL)
    return httpx.Response(status_code, json=json, request=request)


def test_read_root_env_value_trims_quotes_and_whitespace(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n# comment\nDEEPSEEK_API_KEY = ' test-key '\nOTHER=value\n",
        encoding="utf-8",
    )

    assert read_root_env_value("DEEPSEEK_API_KEY", env_path) == "test-key"


def test_get_deepseek_api_key_prefers_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-key")

    assert get_deepseek_api_key() == "env-key"


def test_get_deepseek_api_key_reports_missing_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr("app.deepseek.ROOT_ENV_PATH", tmp_path / ".env")

    with pytest.raises(DeepSeekConfigurationError, match="DEEPSEEK_API_KEY"):
        get_deepseek_api_key()


def test_create_chat_completion_posts_to_deepseek(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_post(
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
        timeout: float,
    ) -> httpx.Response:
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return build_response(
            200,
            json={"choices": [{"message": {"content": "4"}}]},
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    answer = create_chat_completion(
        [{"role": "user", "content": "What is 2+2?"}],
        api_key="secret-key",
        timeout=5.0,
    )

    assert answer == "4"
    assert captured["url"] == DEEPSEEK_API_URL
    assert captured["headers"] == {
        "Authorization": "Bearer secret-key",
        "Content-Type": "application/json",
    }
    assert captured["json"] == {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "thinking": {"type": "disabled"},
        "stream": False,
    }
    assert captured["timeout"] == 5.0


def test_create_chat_completion_sends_response_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_post(
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
        timeout: float,
    ) -> httpx.Response:
        captured["json"] = json
        return build_response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    create_chat_completion(
        [{"role": "user", "content": "Return JSON."}],
        api_key="secret-key",
        response_format={"type": "json_object"},
    )

    assert captured["json"] == {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": "Return JSON."}],
        "thinking": {"type": "disabled"},
        "stream": False,
        "response_format": {"type": "json_object"},
    }


def test_create_chat_completion_maps_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
        timeout: float,
    ) -> httpx.Response:
        request = httpx.Request("POST", url)
        return httpx.Response(401, request=request)

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(DeepSeekAPIError, match="HTTP 401"):
        create_chat_completion(
            [{"role": "user", "content": "What is 2+2?"}],
            api_key="secret-key",
        )


def test_create_chat_completion_rejects_missing_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
        timeout: float,
    ) -> httpx.Response:
        return build_response(200, json={"choices": []})

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(DeepSeekAPIError, match="assistant content"):
        create_chat_completion(
            [{"role": "user", "content": "What is 2+2?"}],
            api_key="secret-key",
        )
