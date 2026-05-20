import json
import os
from pathlib import Path

from kuba.config import load_dotenv_file
from kuba.providers.fixture import FixtureScriptProvider
from kuba.providers.fake import FakeScriptProvider


def test_load_dotenv_file_sets_missing_values_without_overriding_existing(
    tmp_path: Path, monkeypatch
):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "KOKORO_MODEL_PATH=C:\\Users\\HP\\model.pth",
                "KOKORO_VOICE=af_heart",
                "EXISTING=from_file",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("KOKORO_MODEL_PATH", raising=False)
    monkeypatch.setenv("EXISTING", "from_shell")

    loaded = load_dotenv_file(env_path)

    assert loaded["KOKORO_MODEL_PATH"] == "C:\\Users\\HP\\model.pth"
    assert os.environ["KOKORO_MODEL_PATH"] == "C:\\Users\\HP\\model.pth"
    assert os.environ["EXISTING"] == "from_shell"


def test_fixture_script_provider_loads_valid_blueprint_and_rewrites_episode_id(
    tmp_path: Path,
):
    fixture_path = tmp_path / "blueprint.json"
    payload = FakeScriptProvider().generate_script("# Old Title", "old-id")
    fixture_path.write_text(json.dumps(payload), encoding="utf-8")

    generated = FixtureScriptProvider(fixture_path).generate_script(
        "# The River's Debt", "the-rivers-debt"
    )

    assert generated["episode"]["id"] == "the-rivers-debt"
    assert generated["episode"]["title"] == "The River's Debt"
    assert generated["motion_shots"][0]["provider"] == "fixture"
