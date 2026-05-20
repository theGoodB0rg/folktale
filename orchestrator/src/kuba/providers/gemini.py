from __future__ import annotations

import json
import os
from typing import Any
from urllib.request import Request, urlopen

from kuba.blueprint.schema import Blueprint


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash") -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required")
        self.model = model

    def generate_json(self, prompt: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        if schema:
            payload["generationConfig"]["response_json_schema"] = schema
        request = Request(
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model}:generateContent?key={self.api_key}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)


class GeminiScriptProvider:
    provider_name = "gemini"

    def __init__(self, client: GeminiClient | Any | None = None) -> None:
        self.client = client or GeminiClient()

    def generate_script(self, source_markdown: str, episode_id: str) -> dict[str, Any]:
        prompt = (
            "Generate a Kuba-Engine vertical slice blueprint JSON for this source. "
            "Duration must be 60-90 seconds, with two recurring characters, "
            "5-8 scenes, narration segments, and one motion shot. "
            f"Episode id must be {episode_id}.\n\nSOURCE:\n{source_markdown}"
        )
        payload = self.client.generate_json(prompt, schema=Blueprint.model_json_schema())
        payload.setdefault("episode", {})["id"] = episode_id
        return payload
