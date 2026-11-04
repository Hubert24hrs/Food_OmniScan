"""LLM provider abstraction (Gemini today; swap-in providers implement `AIProvider`).

Grounding rules enforced here:
- The model only receives structured data that we already hold (product record, knowledge
  base entries, score adjustments, sources). It's told to refuse anything outside that.
- Model output never writes product data. Vision extraction results are returned to the
  user for review and correction before anything is saved.
"""

import base64
import json
from dataclasses import dataclass

import httpx

from app.core.config import get_settings


class AINotConfigured(Exception):
    pass


class AIError(Exception):
    pass


@dataclass
class AIResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str

    def json(self) -> dict:
        t = self.text.strip()
        if t.startswith("```"):
            t = t.strip("`")
            t = t[t.find("{") :] if "{" in t else t
        start, end = t.find("{"), t.rfind("}")
        if start == -1 or end == -1:
            raise AIError("Model did not return JSON")
        return json.loads(t[start : end + 1])


class AIProvider:
    name = "base"

    def generate(
        self,
        system: str,
        messages: list[dict],
        *,
        images: list[tuple[str, bytes]] | None = None,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> AIResult:
        raise NotImplementedError


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self) -> None:
        s = get_settings()
        if not s.gemini_api_key:
            raise AINotConfigured("GEMINI_API_KEY is not set")
        self.key, self.model, self.base = s.gemini_api_key, s.gemini_model, s.gemini_base_url

    def generate(self, system, messages, *, images=None, json_mode=False, temperature=0.2) -> AIResult:
        contents = []
        for i, m in enumerate(messages):
            parts: list[dict] = [{"text": m["content"]}]
            if images and i == len(messages) - 1:
                for mime, data in images:
                    parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}})
            contents.append({"role": "model" if m["role"] == "assistant" else "user", "parts": parts})
        body: dict = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": 2048},
        }
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        try:
            with httpx.Client(timeout=45.0) as c:
                r = c.post(
                    f"{self.base}/models/{self.model}:generateContent", json=body, headers={"x-goog-api-key": self.key}
                )
        except httpx.HTTPError as e:
            raise AIError(f"Gemini request failed: {e}") from e
        if r.status_code != 200:
            raise AIError(f"Gemini returned {r.status_code}: {r.text[:300]}")
        data = r.json()
        try:
            text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError) as e:
            raise AIError(f"Gemini returned no content ({data.get('promptFeedback')})") from e
        usage = data.get("usageMetadata", {})
        return AIResult(
            text, usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0), self.model, self.name
        )


def get_provider() -> AIProvider:
    s = get_settings()
    if s.ai_provider == "gemini":
        return GeminiProvider()
    raise AINotConfigured("AI provider disabled")
