"""Thin wrapper around the Groq chat API. The same model and settings serve both conditions."""
from __future__ import annotations

import os
import time

from dotenv import load_dotenv

from .kg import ROOT

load_dotenv(ROOT / ".env")

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))          # includes the model's hidden reasoning tokens
REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "medium")  # gpt-oss models only
PROMPTS = ROOT / "prompts"


def prompt(name: str) -> str:
    return (PROMPTS / f"{name}.txt").read_text(encoding="utf-8")


def has_key() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def chat(system: str, user: str, retries: int = 3) -> tuple[str, float]:
    """Return (answer text, seconds). Same model, temperature and token limit for every call."""
    from groq import Groq

    if not has_key():
        raise RuntimeError("GROQ_API_KEY is not set. Copy .env.example to .env and add your key.")
    client = Groq()
    for attempt in range(retries):
        try:
            t0 = time.time()
            extra = {"reasoning_effort": REASONING_EFFORT} if "gpt-oss" in MODEL else {}
            resp = client.chat.completions.create(
                model=MODEL, temperature=TEMPERATURE, max_tokens=MAX_TOKENS, **extra,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
            text = (resp.choices[0].message.content or "").strip()
            # normalise typography the model likes (zero-width spaces, non-breaking hyphens/spaces)
            for a, b in (("​", ""), ("‑", "-"), ("‐", "-"), (" ", " "), (" ", " "),
                         ("【", "["), ("】", "]")):
                text = text.replace(a, b)
            if not text:
                raise RuntimeError("empty completion (token limit reached during reasoning)")
            return text, time.time() - t0
        except Exception as e:  # rate limits on the free tier: back off and retry
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))
            last = e  # noqa: F841
    raise RuntimeError("unreachable")
