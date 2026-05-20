from pathlib import Path
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
