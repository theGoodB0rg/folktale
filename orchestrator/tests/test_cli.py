from pathlib import Path

from typer.testing import CliRunner

from kuba.cli import app
from kuba.config import load_config


def test_cli_help_renders():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Kuba" in result.stdout


def test_load_config_reads_default_yaml(repo_root: Path):
    config = load_config(repo_root / "config" / "default.yaml")

    assert config.render.fps == 30
    assert config.render.preview.width == 1280
    assert config.render.preview.height == 720
    assert config.render.final.width == 1920
    assert config.render.final.height == 1080
    assert config.comfy.base_url == "http://127.0.0.1:8188"
    assert config.comfy.workflow_path == "config/comfy/workflows/sdxl_ip_adapter_api.json"
    assert config.comfy.workflow_map_path == "config/comfy/workflows/sdxl_ip_adapter_api.map.yaml"
