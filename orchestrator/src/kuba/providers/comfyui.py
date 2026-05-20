from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml

from kuba.paths import resolve_episode_path


class ComfyUIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8188", timeout_sec: float = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def post_prompt(self, prompt: dict[str, Any]) -> str:
        payload = json.dumps({"prompt": prompt}).encode("utf-8")
        request = Request(
            f"{self.base_url}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_sec) as response:
            data = json.loads(response.read().decode("utf-8"))
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return prompt_id")
        return str(prompt_id)

    def wait_for_output_image(
        self,
        prompt_id: str,
        *,
        poll_interval_sec: float = 1,
        timeout_sec: float = 300,
    ) -> dict[str, str]:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            with urlopen(f"{self.base_url}/history/{prompt_id}", timeout=self.timeout_sec) as response:
                history = json.loads(response.read().decode("utf-8"))
            image = _first_history_image(history, prompt_id)
            if image:
                return image
            time.sleep(poll_interval_sec)
        raise TimeoutError(f"ComfyUI prompt timed out: {prompt_id}")

    def download_image(self, image_ref: dict[str, str]) -> bytes:
        query = urlencode(
            {
                "filename": image_ref["filename"],
                "subfolder": image_ref.get("subfolder", ""),
                "type": image_ref.get("type", "output"),
            }
        )
        with urlopen(f"{self.base_url}/view?{query}", timeout=self.timeout_sec) as response:
            return response.read()


class ComfyUIImageProvider:
    provider_name = "comfyui"

    def __init__(
        self,
        *,
        workflow_path: Path,
        workflow_map_path: Path,
        client: ComfyUIClient | Any | None = None,
    ) -> None:
        self.workflow_path = workflow_path
        self.workflow_map_path = workflow_map_path
        self.client = client or ComfyUIClient()

    def generate_image(self, episode_root: str, relative_path: str, seed_text: str) -> str:
        workflow = json.loads(self.workflow_path.read_text(encoding="utf-8"))
        mapping = yaml.safe_load(self.workflow_map_path.read_text(encoding="utf-8")) or {}
        output_path = resolve_episode_path(Path(episode_root), relative_path)
        output_prefix = output_path.with_suffix("").name
        prompt = patch_workflow(
            workflow,
            mapping,
            positive_prompt=seed_text,
            negative_prompt="",
            seed=0,
            output_prefix=output_prefix,
            reference_image_path=None,
        )
        prompt_id = self.client.post_prompt(prompt)
        image_ref = self.client.wait_for_output_image(prompt_id)
        image_bytes = self.client.download_image(image_ref)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        return str(output_path)


def patch_workflow(
    workflow: dict[str, Any],
    mapping: dict[str, str],
    *,
    positive_prompt: str,
    negative_prompt: str,
    seed: int,
    output_prefix: str,
    reference_image_path: str | None,
) -> dict[str, Any]:
    patched = deepcopy(workflow)
    values: dict[str, Any] = {
        "positive_prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "seed": seed,
        "save_prefix": output_prefix,
        "reference_image": reference_image_path,
    }
    for key, value in values.items():
        target = mapping.get(key)
        if target and value is not None:
            _set_path(patched, target, value)
    return patched


def _set_path(data: dict[str, Any], dotted_path: str, value: Any) -> None:
    current: Any = data
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        current = current[part]
    current[parts[-1]] = value


def _first_history_image(history: dict[str, Any], prompt_id: str) -> dict[str, str] | None:
    outputs = history.get(prompt_id, history).get("outputs", {})
    for output in outputs.values():
        images = output.get("images") or []
        if images:
            return images[0]
    return None
