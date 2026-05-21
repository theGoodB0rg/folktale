from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml

from kuba.paths import resolve_episode_path


class ComfyUIClient:
    def __init__(self, base_url: str | None = None, timeout_sec: float = 30):
        self.base_url = (base_url or os.environ.get("COMFYUI_BASE_URL") or "http://127.0.0.1:8188").rstrip("/")
        self.timeout_sec = timeout_sec

    def upload_image(self, image_bytes: bytes, filename: str) -> str:
        boundary = b"----ComfyUIFormBoundary" + str(time.time()).encode()
        body = b""
        body += b"--" + boundary + b"\r\n"
        body += f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode()
        body += b"Content-Type: image/png\r\n\r\n"
        body += image_bytes
        body += b"\r\n"
        body += b"--" + boundary + b"--\r\n"

        request = Request(
            f"{self.base_url}/upload/image",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_sec) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data.get("name", filename))

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

    def generate_image(
        self,
        episode_root: str,
        relative_path: str,
        seed_text: str,
        reference_image_path: str | None = None,
    ) -> str:
        workflow = json.loads(self.workflow_path.read_text(encoding="utf-8"))
        mapping = yaml.safe_load(self.workflow_map_path.read_text(encoding="utf-8")) or {}
        output_path = resolve_episode_path(Path(episode_root), relative_path)
        output_prefix = output_path.with_suffix("").name

        image_reference: str | None = None
        if reference_image_path is not None:
            ref_full_path = resolve_episode_path(Path(episode_root), reference_image_path)
            if ref_full_path.exists():
                ref_bytes = ref_full_path.read_bytes()
                image_reference = self.client.upload_image(ref_bytes, ref_full_path.name)

        prompt = patch_workflow(
            workflow,
            mapping,
            positive_prompt=seed_text,
            negative_prompt="",
            seed=0,
            output_prefix=output_prefix,
            reference_image_path=image_reference,
        )
        prompt_id = self.client.post_prompt(prompt)
        image_ref = self.client.wait_for_output_image(prompt_id)
        image_bytes = self.client.download_image(image_ref)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        return str(output_path)

    def smoke_generate(self, episode_root: Path) -> Path:
        return Path(
            self.generate_image(
                str(episode_root),
                "images/scenes/comfy_smoke.png",
                "tiny smoke test image, simple river stone",
            )
        )


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
    if reference_image_path is None:
        _bypass_ip_adapter(patched)
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


def _bypass_ip_adapter(workflow: dict[str, Any]) -> None:
    ip_adapter_ids = [
        node_id
        for node_id, node in workflow.items()
        if node.get("class_type") in {"IPAdapter", "IPAdapterUnifiedLoader", "LoadImage"}
    ]
    model_input = _first_upstream_model_input(workflow, ip_adapter_ids)
    if model_input is not None:
        for node in workflow.values():
            inputs = node.get("inputs", {})
            if inputs.get("model") in [[node_id, 0] for node_id in ip_adapter_ids]:
                inputs["model"] = model_input
    for node_id in ip_adapter_ids:
        workflow.pop(node_id, None)


def _first_upstream_model_input(
    workflow: dict[str, Any],
    node_ids: list[str],
) -> list[str] | None:
    for node_id in node_ids:
        model_input = workflow.get(node_id, {}).get("inputs", {}).get("model")
        if isinstance(model_input, list) and len(model_input) == 2:
            return model_input
    return None


def validate_workflow_map(workflow: dict[str, Any], mapping: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for key, dotted_path in mapping.items():
        try:
            _get_path(workflow, dotted_path)
        except (KeyError, TypeError) as exc:
            errors.append(f"workflow map entry {key} does not match workflow path {dotted_path}: {exc}")
    return errors


def _set_path(data: dict[str, Any], dotted_path: str, value: Any) -> None:
    current: Any = data
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        current = current[part]
    current[parts[-1]] = value


def _get_path(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        current = current[part]
    return current


def _first_history_image(history: dict[str, Any], prompt_id: str) -> dict[str, str] | None:
    outputs = history.get(prompt_id, history).get("outputs", {})
    for output in outputs.values():
        images = output.get("images") or []
        if images:
            return images[0]
    return None
