"""
Reusable async Ollama client.

Provides helpers for text generation, JSON-structured output,
and automatic model selection (fast vs slow).
"""

from __future__ import annotations

import json
import asyncio
import time
from typing import Any, Optional

import aiohttp
from loguru import logger

from app.config import ollama_cfg


# Maximum retries for transient failures
_MAX_RETRIES = 3
_RETRY_DELAY = 2  # seconds
_REQUEST_TIMEOUT = 180  # seconds (local models can be slow)

# Global lock to prevent concurrent Ollama requests which can cause 500 errors
_ollama_lock = asyncio.Lock()


async def _post(
    model: str,
    prompt: str,
    *,
    system: Optional[str] = None,
    temperature: float = 0.7,
    timeout: int = _REQUEST_TIMEOUT,
) -> str:
    """
    Send a prompt to Ollama and return the generated text.

    Retries up to ``_MAX_RETRIES`` times on transient errors.
    """
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    if system:
        payload["system"] = system

    last_error: Optional[Exception] = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with _ollama_lock:
                    async with session.post(
                        ollama_cfg.ollama_url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                    ) as resp:
                        if resp.status != 200:
                            err_text = await resp.text()
                            raise aiohttp.ClientResponseError(
                                resp.request_info,
                                resp.history,
                                status=resp.status,
                                message=f"Ollama returned {resp.status}: {err_text}"
                            )
                        data = await resp.json()
                        text: str = data.get("response", "")
                        logger.debug(
                            "Ollama [{} | attempt {}] → {} chars",
                            model,
                            attempt,
                            len(text),
                        )
                        return text.strip()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            last_error = exc
            logger.warning(
                "Ollama request attempt {}/{} failed: {}",
                attempt,
                _MAX_RETRIES,
                exc,
            )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_DELAY * attempt)

    raise RuntimeError(
        f"Ollama request failed after {_MAX_RETRIES} attempts: {last_error}"
    )


async def _post_timed(
    model: str,
    prompt: str,
    *,
    system: Optional[str] = None,
    temperature: float = 0.7,
    timeout: int = _REQUEST_TIMEOUT,
) -> tuple[str, int]:
    """Like _post but also returns processing time in milliseconds."""
    start = time.monotonic()
    result = await _post(model, prompt, system=system,
                         temperature=temperature, timeout=timeout)
    elapsed_ms = int((time.monotonic() - start) * 1000)
    return result, elapsed_ms


# ── Public helpers ──────────────────────────────────────────────


async def generate_text(
    prompt: str,
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.7,
) -> str:
    """Generate free-form text using the specified (or slow) model."""
    model = model or ollama_cfg.model_slow
    return await _post(model, prompt, system=system, temperature=temperature)


async def generate_text_timed(
    prompt: str,
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.7,
) -> tuple[str, int]:
    """Generate text and return (text, processing_time_ms)."""
    model = model or ollama_cfg.model_slow
    return await _post_timed(model, prompt, system=system, temperature=temperature)


async def generate_json(
    prompt: str,
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.3,
) -> dict[str, Any]:
    """
    Generate text and parse the first JSON object found in the response.

    Falls back to a wrapper dict ``{"raw": <text>}`` if parsing fails.
    """
    model = model or ollama_cfg.model_slow
    raw = await _post(model, prompt, system=system, temperature=temperature)

    # Try to extract JSON from the response
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Look for JSON between ```json ... ``` markers
    if "```json" in raw:
        try:
            start = raw.index("```json") + 7
            end = raw.index("```", start)
            return json.loads(raw[start:end].strip())
        except (ValueError, json.JSONDecodeError):
            pass

    # Look for the first { ... } block
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        pass

    logger.warning("Could not parse JSON from Ollama response, returning raw wrapper")
    return {"raw": raw}


async def generate_json_timed(
    prompt: str,
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.3,
) -> tuple[dict[str, Any], str, int]:
    """
    Generate JSON and return (parsed_dict, raw_response, processing_time_ms).
    """
    model = model or ollama_cfg.model_slow
    start = time.monotonic()
    raw = await _post(model, prompt, system=system, temperature=temperature)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    # Parse JSON
    parsed: dict[str, Any] = {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        pass

    if not parsed and "```json" in raw:
        try:
            s = raw.index("```json") + 7
            e = raw.index("```", s)
            parsed = json.loads(raw[s:e].strip())
        except (ValueError, json.JSONDecodeError):
            pass

    if not parsed:
        try:
            s = raw.index("{")
            e = raw.rindex("}") + 1
            parsed = json.loads(raw[s:e])
        except (ValueError, json.JSONDecodeError):
            parsed = {"raw": raw}

    return parsed, raw, elapsed_ms


async def fast_completion(
    prompt: str,
    *,
    system: Optional[str] = None,
    temperature: float = 0.7,
) -> str:
    """Quick completion using the fast (phi3) model."""
    return await _post(
        ollama_cfg.model_fast, prompt, system=system, temperature=temperature
    )


async def slow_completion(
    prompt: str,
    *,
    system: Optional[str] = None,
    temperature: float = 0.7,
) -> str:
    """Deep-reasoning completion using the slow (llama3) model."""
    return await _post(
        ollama_cfg.model_slow, prompt, system=system, temperature=temperature
    )


async def auto_completion(
    prompt: str,
    *,
    system: Optional[str] = None,
    temperature: float = 0.7,
    complexity: str = "auto",
) -> str:
    """
    Automatically pick the right model based on prompt complexity.

    complexity:
      - "simple"  → always phi3
      - "complex" → always llama3
      - "auto"    → phi3 if prompt < 200 chars, else llama3
    """
    if complexity == "simple":
        model = ollama_cfg.model_fast
    elif complexity == "complex":
        model = ollama_cfg.model_slow
    else:
        model = (
            ollama_cfg.model_fast
            if len(prompt) < 200
            else ollama_cfg.model_slow
        )

    logger.debug("auto_completion selected model={}", model)
    return await _post(model, prompt, system=system, temperature=temperature)


async def check_health() -> bool:
    """Return True if the Ollama server is reachable."""
    try:
        base_url = ollama_cfg.ollama_url.replace("/api/generate", "")
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                return resp.status == 200
    except Exception:
        return False
