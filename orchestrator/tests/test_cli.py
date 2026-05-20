from pathlib import Path

from kuba.config import load_config


def test_load_config_reads_default_yaml(repo_root: Path):
    config = load_config(repo_root / "config" / "default.yaml")

    assert config.render.preview.width == 1280
    assert config.render.preview.height == 720
    assert config.render.final.width == 1920
    assert config.render.final.height == 1080
    assert config.comfy.base_url == "http://127.0.0.1:8188"
