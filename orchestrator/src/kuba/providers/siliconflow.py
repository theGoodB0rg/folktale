from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any
from urllib.request import Request, urlopen

from kuba.paths import resolve_episode_path


class SiliconFlowClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.siliconflow.com/v1",
        model: str = "Wan-AI/Wan2.2-T2V-A14B",
    ) -> None:
        self.api_key = api_key or os.environ.get("SILICONFLOW_API_KEY")
        if not self.api_key:
            raise RuntimeError("SILICONFLOW_API_KEY is required")
        self.base_url = base_url.rstrip("/")
        self.model = model

    def submit_video(self, prompt: str, source_image_path: str, duration_sec: float) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "image_size": "1280x720",
        }
        request = Request(
            f"{self.base_url}/video/submit",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
        request_id = data.get("requestId")
        if not request_id:
            raise RuntimeError("SiliconFlow did not return requestId")
        return str(request_id)

    def wait_for_video_bytes(self, request_id: str) -> bytes:
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            status = self._status(request_id)
            state = status.get("status")
            if state == "Succeed":
                videos = status.get("results", {}).get("videos", [])
                if not videos or not videos[0].get("url"):
                    raise RuntimeError("SiliconFlow succeeded without video URL")
                with urlopen(videos[0]["url"], timeout=300) as response:
                    return response.read()
            if state == "Failed":
                raise RuntimeError(f"SiliconFlow video failed: {status.get('reason', '')}")
            time.sleep(10)
        raise TimeoutError(f"SiliconFlow request timed out: {request_id}")

    def _status(self, request_id: str) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}/video/status",
            data=json.dumps({"requestId": request_id}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))


class SiliconFlowVideoProvider:
    provider_name = "siliconflow"

    def __init__(self, client: SiliconFlowClient | Any | None = None) -> None:
        self.client = client or SiliconFlowClient()

    def generate_video(
        self,
        episode_root: str,
        relative_path: str,
        source_image_path: str,
        prompt: str,
        duration_sec: float,
    ) -> str:
        output_path = resolve_episode_path(Path(episode_root), relative_path)
        request_id = self.client.submit_video(prompt, source_image_path, duration_sec)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self.client.wait_for_video_bytes(request_id))
        return str(output_path)
