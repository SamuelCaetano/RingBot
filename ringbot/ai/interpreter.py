"""AI interpreter: natural-language description -> validated RingSpec."""

from __future__ import annotations

import json
import random
import re

from ringbot.ai.prompts import SYSTEM_PROMPT
from ringbot.ai.providers import LLMProvider, get_provider
from ringbot.models.ring_spec import RingSpec


MAX_RETRIES = 3


def _extract_json(text: str) -> str:
    """Strip markdown code fences or other wrapping from the LLM response."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        return text[brace_start : brace_end + 1]
    return text


def interpret_description(
    description: str,
    *,
    provider_name: str | None = None,
    ring_size: float | None = None,
    design_seed: int | None = None,
) -> RingSpec:
    """Use an LLM to convert a ring description into a validated RingSpec.

    Retries up to MAX_RETRIES times on parse/validation failure, feeding
    the error back to the model so it can self-correct.
    """
    from ringbot.config import get_default_provider, get_default_ring_size

    provider_name = provider_name or get_default_provider()
    ring_size = ring_size or get_default_ring_size()
    seed = design_seed if design_seed is not None else random.randint(0, 2**31)

    provider: LLMProvider = get_provider(provider_name)

    user_msg = (
        f"Design a ring based on this description:\n\n\"{description}\"\n\n"
        f"The ring size is US {ring_size}."
    )

    last_error = ""
    for attempt in range(MAX_RETRIES):
        if last_error:
            user_msg_full = (
                f"{user_msg}\n\nYour previous response had an error:\n{last_error}\n"
                "Please fix the JSON and try again."
            )
        else:
            user_msg_full = user_msg

        raw = provider.chat(SYSTEM_PROMPT, user_msg_full)
        json_str = _extract_json(raw)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            last_error = f"JSON parse error: {exc}"
            continue

        if "band" in data and ring_size is not None:
            data["band"]["us_size"] = ring_size

        data["design_seed"] = seed
        data["description"] = description

        try:
            spec = RingSpec.model_validate(data)
            return spec
        except Exception as exc:
            last_error = f"Validation error: {exc}"
            continue

    raise RuntimeError(
        f"Failed to get valid RingSpec after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )
