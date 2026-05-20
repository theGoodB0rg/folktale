from pathlib import Path
import os
from typing import Any

import yaml
from pydantic import BaseModel


class RenderSize(BaseModel):
    width: int
    height: int


class RenderConfig(BaseModel):
    fps: int
    preview: RenderSize
    final: RenderSize


class ComfyConfig(BaseModel):
    base_url: str
    workflow_path: str
    workflow_map_path: str


class Config(BaseModel):
    render: RenderConfig
    comfy: ComfyConfig


def load_config(path: Path) -> Config:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Config.model_validate(data)


def load_dotenv_file(path: Path, *, override: bool = False) -> dict[str, str]:
    if not path.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_env_value(value.strip())
        if not key:
            continue
        loaded[key] = value
        if override or key not in os.environ:
            os.environ[key] = value
    return loaded


def load_project_env(start: Path | None = None) -> dict[str, str]:
    current = (start or Path.cwd()).resolve()
    candidates = [current, *current.parents]
    loaded: dict[str, str] = {}
    for directory in candidates:
        env_path = directory / ".env"
        if env_path.exists():
            loaded.update(load_dotenv_file(env_path))
            break
    return loaded


def _strip_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
