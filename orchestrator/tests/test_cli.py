from pathlib import Path

from typer.testing import CliRunner

from kuba.cli import app
from kuba.config import load_config
from kuba.providers.fake import FailingFakeVideoProvider, FakeAudioProvider, FakeImageProvider


def test_cli_help_renders():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Kuba" in result.stdout


def test_cli_doctor_runs_in_check_only_mode():
    result = CliRunner().invoke(app, ["doctor", "--check", "python"])

    assert result.exit_code == 0
    assert "python" in result.stdout.lower()


def test_cli_doctor_reports_missing_real_dependency(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = CliRunner().invoke(app, ["doctor", "--check", "gemini"])

    assert result.exit_code == 1
    assert "missing" in result.stdout.lower()


def test_cli_create_episode(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "episode",
            "create",
            "--output-root",
            str(tmp_path),
            "--title",
            "The River's Debt",
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "the-rivers-debt" / "script" / "source.md").exists()


def test_cli_fake_flow_generates_and_validates_episode(tmp_path):
    create_result = CliRunner().invoke(
        app,
        [
            "episode",
            "create",
            "--output-root",
            str(tmp_path),
            "--title",
            "The River's Debt",
        ],
    )
    assert create_result.exit_code == 0
    episode_root = tmp_path / "the-rivers-debt"

    script_result = CliRunner().invoke(
        app, ["script", "generate", str(episode_root), "--fake"]
    )
    refs_result = CliRunner().invoke(
        app, ["refs", "generate", str(episode_root), "--fake"]
    )
    approve_result = CliRunner().invoke(app, ["refs", "approve", str(episode_root)])
    assets_result = CliRunner().invoke(
        app, ["assets", "generate", str(episode_root), "--fake"]
    )
    validate_result = CliRunner().invoke(app, ["assets", "validate", str(episode_root)])

    assert script_result.exit_code == 0
    assert refs_result.exit_code == 0
    assert approve_result.exit_code == 0
    assert assets_result.exit_code == 0
    assert validate_result.exit_code == 0
    assert (episode_root / "images" / "fallback_stills" / "motion_0001_fallback.png").exists()


def test_cli_script_generate_requires_fake_provider(tmp_path):
    create_result = CliRunner().invoke(
        app,
        [
            "episode",
            "create",
            "--output-root",
            str(tmp_path),
            "--title",
            "The River's Debt",
        ],
    )
    assert create_result.exit_code == 0

    result = CliRunner().invoke(
        app, ["script", "generate", str(tmp_path / "the-rivers-debt")]
    )

    assert result.exit_code != 0
    assert "--provider" in result.stdout


def test_cli_script_generate_accepts_gemini_provider(monkeypatch, tmp_path):
    create_result = CliRunner().invoke(
        app,
        [
            "episode",
            "create",
            "--output-root",
            str(tmp_path),
            "--title",
            "The River's Debt",
        ],
    )
    assert create_result.exit_code == 0
    episode = tmp_path / "the-rivers-debt"
    called = {}

    class Provider:
        def generate_script(self, source_markdown, episode_id):
            called["episode_id"] = episode_id
            return FakePayload.script(episode_id)

    monkeypatch.setattr("kuba.cli.GeminiScriptProvider", lambda: Provider())

    result = CliRunner().invoke(app, ["script", "generate", str(episode), "--provider", "gemini"])

    assert result.exit_code == 0
    assert called["episode_id"] == "the-rivers-debt"


def test_cli_refs_generate_accepts_comfy_provider(monkeypatch, tmp_path):
    episode = _prepared_episode(tmp_path)
    generated = []

    class Provider:
        provider_name = "comfyui"

        def generate_image(self, episode_root, relative_path, seed_text):
            generated.append(relative_path)
            return FakeImageProvider().generate_image(episode_root, relative_path, seed_text)

    monkeypatch.setattr("kuba.cli._build_image_provider", lambda provider, **kwargs: Provider())

    result = CliRunner().invoke(app, ["refs", "generate", str(episode), "--provider", "comfy"])

    assert result.exit_code == 0
    assert "images/characters/protagonist_ref.png" in generated


def test_cli_assets_generate_accepts_real_provider_names(monkeypatch, tmp_path):
    episode = _prepared_episode(tmp_path)
    CliRunner().invoke(app, ["refs", "generate", str(episode), "--fake"])
    CliRunner().invoke(app, ["refs", "approve", str(episode)])

    monkeypatch.setattr("kuba.cli._build_audio_provider", lambda provider: FakeAudioProvider())
    monkeypatch.setattr("kuba.cli._build_image_provider", lambda provider, **kwargs: FakeImageProvider())
    monkeypatch.setattr("kuba.cli._build_video_provider", lambda provider: FailingFakeVideoProvider())

    result = CliRunner().invoke(
        app,
        [
            "assets",
            "generate",
            str(episode),
            "--audio-provider",
            "kokoro",
            "--image-provider",
            "comfy",
            "--video-provider",
            "veo",
        ],
    )

    assert result.exit_code == 0


class FakePayload:
    @staticmethod
    def script(episode_id: str):
        from kuba.providers.fake import FakeScriptProvider

        return FakeScriptProvider().generate_script(f"# {episode_id}", episode_id)


def _prepared_episode(tmp_path: Path) -> Path:
    episode = tmp_path / "the-rivers-debt"
    create_result = CliRunner().invoke(
        app,
        [
            "episode",
            "create",
            "--output-root",
            str(tmp_path),
            "--title",
            "The River's Debt",
        ],
    )
    assert create_result.exit_code == 0
    script_result = CliRunner().invoke(app, ["script", "generate", str(episode), "--fake"])
    assert script_result.exit_code == 0
    return episode


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
