from dataclasses import dataclass
import json
import os
from pathlib import Path
import platform
import shutil
import sys
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import urlopen

import yaml

from kuba.config import load_project_env
from kuba.providers.comfyui import validate_workflow_map


def run_python_check() -> str:
    version = platform.python_version()
    executable = sys.executable
    return f"python {version} ({executable})"


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    message: str


def check_env(name: str) -> CheckResult:
    if os.environ.get(name):
        return CheckResult(f"env:{name}", True, "present")
    return CheckResult(f"env:{name}", False, "missing")


def check_path(name: str, value: str | None) -> CheckResult:
    if not value:
        return CheckResult(name, False, "missing")
    path = Path(value)
    if path.exists():
        return CheckResult(name, True, str(path))
    return CheckResult(name, False, f"missing: {path}")


def check_comfy(
    base_url: str | None = None,
    *,
    get_json: Callable[[str, float], dict[str, Any]] | None = None,
) -> CheckResult:
    base = (base_url or os.environ.get("COMFYUI_BASE_URL") or "http://127.0.0.1:8188").rstrip("/")
    getter = get_json or _http_get_json
    try:
        getter(f"{base}/system_stats", 3)
    except Exception as exc:
        return CheckResult("comfy", False, f"unreachable: {exc}")
    return CheckResult("comfy", True, f"reachable: {base}")


def check_executable(name: str) -> CheckResult:
    found = _which(name)
    if found:
        return CheckResult(name, True, found)
    return CheckResult(name, False, "missing")


def check_remotion() -> CheckResult:
    root = Path(os.environ.get("KUBA_REMOTION_ROOT", _repo_root() / "remotion"))
    package_json = root / "package.json"
    if not package_json.exists():
        return CheckResult("remotion", False, f"missing: {package_json}")
    node_modules = root / "node_modules"
    if node_modules.exists():
        return CheckResult("remotion", True, "dependencies installed")
    if _which("npm"):
        return CheckResult("remotion", True, "dependencies installable with npm")
    return CheckResult("remotion", False, "node_modules missing and npm unavailable")


def check_production() -> CheckResult:
    checks = [
        check_script_provider(),
        run_doctor_check("kokoro"),
        check_comfy(),
        check_path(
            "comfy-workflow",
            os.environ.get("KUBA_COMFY_WORKFLOW")
            or str(_repo_root() / "config" / "comfy" / "workflows" / "sdxl_ip_adapter_api.json"),
        ),
        check_path(
            "comfy-workflow-map",
            os.environ.get("KUBA_COMFY_WORKFLOW_MAP")
            or str(_repo_root() / "config" / "comfy" / "workflows" / "sdxl_ip_adapter_api.map.yaml"),
        ),
        check_comfy_workflow_map(),
        check_executable("ffmpeg"),
        check_executable("ffprobe"),
        _selected_video_provider_check(),
        check_remotion(),
    ]
    failed = [result for result in checks if not result.ok]
    if failed:
        return CheckResult(
            "production",
            False,
            "; ".join(f"{result.name}: {result.message}" for result in failed),
        )
    return CheckResult("production", True, "production checks passed")


def check_script_provider() -> CheckResult:
    provider = os.environ.get("KUBA_SCRIPT_PROVIDER", "gemini").lower()
    if provider == "gemini":
        result = run_doctor_check("gemini")
        return CheckResult("script-provider:gemini", result.ok, result.message)
    if provider == "fixture":
        result = check_path("blueprint-fixture", os.environ.get("KUBA_BLUEPRINT_FIXTURE"))
        if result.ok:
            return CheckResult("script-provider:fixture", True, "fixture present")
        return CheckResult(
            "script-provider:fixture",
            False,
            f"{result.message}; set KUBA_BLUEPRINT_FIXTURE to a validated blueprint JSON",
        )
    return CheckResult("script-provider", False, f"unsupported: {provider}")


def check_comfy_workflow_map() -> CheckResult:
    workflow_path = Path(
        os.environ.get("KUBA_COMFY_WORKFLOW")
        or _repo_root() / "config" / "comfy" / "workflows" / "sdxl_ip_adapter_api.json"
    )
    map_path = Path(
        os.environ.get("KUBA_COMFY_WORKFLOW_MAP")
        or _repo_root() / "config" / "comfy" / "workflows" / "sdxl_ip_adapter_api.map.yaml"
    )
    if not workflow_path.exists() or not map_path.exists():
        return CheckResult(
            "comfy-workflow-map-validation",
            False,
            "workflow or map missing; export a ComfyUI API workflow JSON and set "
            "KUBA_COMFY_WORKFLOW/KUBA_COMFY_WORKFLOW_MAP",
        )
    try:
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        mapping = yaml.safe_load(map_path.read_text(encoding="utf-8")) or {}
        errors = validate_workflow_map(workflow, mapping)
    except Exception as exc:
        return CheckResult("comfy-workflow-map-validation", False, str(exc))
    if errors:
        return CheckResult("comfy-workflow-map-validation", False, "; ".join(errors))
    return CheckResult("comfy-workflow-map-validation", True, "map matches workflow")


def run_doctor_check(check: str) -> CheckResult:
    load_project_env()
    normalized = check.lower()
    if normalized == "python":
        return CheckResult("python", True, run_python_check())
    if normalized == "gemini":
        return check_env("GEMINI_API_KEY")
    if normalized == "comfy":
        return check_comfy()
    if normalized == "kokoro":
        model = check_path("kokoro-model", os.environ.get("KOKORO_MODEL_PATH"))
        voices = check_path("kokoro-voices", os.environ.get("KOKORO_VOICES_PATH"))
        if model.ok and voices.ok:
            return CheckResult("kokoro", True, "model and voices present")
        return CheckResult("kokoro", False, f"{model.message}; {voices.message}")
    if normalized in {"siliconflow", "veo"}:
        return check_env("SILICONFLOW_API_KEY" if normalized == "siliconflow" else "GEMINI_API_KEY")
    if normalized == "ffmpeg":
        return check_executable("ffmpeg")
    if normalized == "ffprobe":
        return check_executable("ffprobe")
    if normalized == "remotion":
        return check_remotion()
    if normalized == "production":
        return check_production()
    raise ValueError(f"unknown doctor check: {check}")


def _http_get_json(url: str, timeout_sec: float) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=timeout_sec) as response:
            return json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(exc.reason) from exc


def _selected_video_provider_check() -> CheckResult:
    selected = os.environ.get("KUBA_VIDEO_PROVIDER", "siliconflow").lower()
    if selected not in {"siliconflow", "veo"}:
        return CheckResult("video-provider", False, f"unsupported: {selected}")
    result = run_doctor_check(selected)
    if result.ok:
        return CheckResult(f"video-provider:{selected}", True, result.message)
    env_name = "SILICONFLOW_API_KEY" if selected == "siliconflow" else "GEMINI_API_KEY"
    return CheckResult(
        f"video-provider:{selected}",
        False,
        f"{result.message}; set {env_name} or change KUBA_VIDEO_PROVIDER",
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _which(name: str) -> str | None:
    return shutil.which(name)
