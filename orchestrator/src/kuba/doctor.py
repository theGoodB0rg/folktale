from dataclasses import dataclass
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import urlopen


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


def run_doctor_check(check: str) -> CheckResult:
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
    raise ValueError(f"unknown doctor check: {check}")


def _http_get_json(url: str, timeout_sec: float) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=timeout_sec) as response:
            return json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(exc.reason) from exc
