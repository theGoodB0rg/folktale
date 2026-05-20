from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any
from urllib.request import Request, urlopen

from kuba.paths import resolve_episode_path


class GeminiVeoClient:
    def __init__(self, api_key: str | None = None, model: str = "veo-3.1-generate-preview") -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required")
        self.model = model

    def submit_video(self, prompt: str, source_image_path: str, duration_sec: float) -> str:
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"durationSeconds": int(duration_sec)},
        }
        request = Request(
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model}:predictLongRunning?key={self.api_key}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
        operation = data.get("name")
        if not operation:
            raise RuntimeError("Veo did not return operation name")
        return str(operation)

    def wait_for_video_bytes(self, operation_id: str) -> bytes:
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            with urlopen(
                "https://generativelanguage.googleapis.com/v1beta/"
                f"{operation_id}?key={self.api_key}",
                timeout=120,
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
            if data.get("done"):
                uri = _extract_video_uri(data)
                with urlopen(uri, timeout=300) as video_response:
                    return video_response.read()
            time.sleep(10)
        raise TimeoutError(f"Veo operation timed out: {operation_id}")


class GeminiVeoVideoProvider:
    provider_name = "veo"

    def __init__(self, client: GeminiVeoClient | Any | None = None) -> None:
        self.client = client or GeminiVeoClient()

    def generate_video(
        self,
        episode_root: str,
        relative_path: str,
        source_image_path: str,
        prompt: str,
        duration_sec: float,
    ) -> str:
        output_path = resolve_episode_path(Path(episode_root), relative_path)
        operation_id = self.client.submit_video(prompt, source_image_path, duration_sec)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self.client.wait_for_video_bytes(operation_id))
        return str(output_path)


def _extract_video_uri(operation: dict[str, Any]) -> str:
    response = operation.get("response") or {}
    candidates = response.get("generateVideoResponse", {}).get("generatedSamples", [])
    if candidates:
        video = candidates[0].get("video", {})
        uri = video.get("uri")
        if uri:
            return str(uri)
    raise RuntimeError("Veo operation completed without downloadable video URI")
