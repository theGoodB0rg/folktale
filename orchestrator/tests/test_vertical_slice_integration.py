from pathlib import Path

import pytest
from pydantic import ValidationError

from kuba.blueprint.loader import load_blueprint
from kuba.phases.episode_create import create_episode
from kuba.phases.script_generate import generate_script
from kuba.providers.fake import FakeScriptProvider
from kuba.state.episode_state import EpisodeState, PhaseStatus


def test_create_episode_and_generate_fake_blueprint(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")

    assert episode_root.name == "the-rivers-debt"
    assert (episode_root / "script" / "source.md").exists()

    generate_script(episode_root, FakeScriptProvider())

    blueprint = load_blueprint(episode_root / "blueprint.json")
    assert blueprint.episode.duration_sec == 78
    assert len(blueprint.characters) == 2
    assert 5 <= len(blueprint.scenes) <= 8
    assert len(blueprint.motion_shots) == 1

    state = EpisodeState.load(episode_root / "state.json")
    assert state.phases["script_generate"] == PhaseStatus.COMPLETED


def test_create_episode_raises_if_episode_directory_already_exists(tmp_path: Path):
    create_episode(tmp_path / "episodes", "The River's Debt")

    with pytest.raises(FileExistsError):
        create_episode(tmp_path / "episodes", "The River's Debt")


def test_create_episode_transliterates_unicode_title(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "Ékó River")

    assert episode_root.name == "eko-river"


def test_create_episode_preserves_non_latin_alphanumeric_title(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "漢字")

    assert episode_root.name == "漢字"


def test_create_episode_preserves_mixed_unicode_alphanumeric_title(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "River 漢字 Tale")

    assert episode_root.name == "river-漢字-tale"


def test_create_episode_raises_when_title_has_no_alphanumeric_slug_characters(tmp_path: Path):
    with pytest.raises(ValueError, match="alphanumeric"):
        create_episode(tmp_path / "episodes", "!!!")


def test_generate_script_uses_episode_directory_slug_as_blueprint_id(tmp_path: Path):
    first_episode = create_episode(tmp_path / "episodes", "The River's Debt")
    second_episode = create_episode(tmp_path / "episodes", "Ékó River")

    generate_script(first_episode, FakeScriptProvider())
    generate_script(second_episode, FakeScriptProvider())

    assert load_blueprint(first_episode / "blueprint.json").episode.id == "the-rivers-debt"
    assert load_blueprint(second_episode / "blueprint.json").episode.id == "eko-river"


def test_generate_script_validates_before_replacing_files_or_completing_phase(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    original_blueprint = (episode_root / "blueprint.json").read_text(encoding="utf-8")
    original_generated_script = (episode_root / "script" / "generated_script.json").read_text(
        encoding="utf-8"
    )
    EpisodeState.new().save(episode_root / "state.json")

    with pytest.raises(ValidationError, match="duration"):
        generate_script(episode_root, InvalidDurationScriptProvider())

    assert (episode_root / "blueprint.json").read_text(encoding="utf-8") == original_blueprint
    assert (
        episode_root / "script" / "generated_script.json"
    ).read_text(encoding="utf-8") == original_generated_script
    assert "script_generate" not in EpisodeState.load(episode_root / "state.json").phases


class InvalidDurationScriptProvider:
    def generate_script(self, source_markdown: str, episode_id: str) -> dict[str, object]:
        payload = FakeScriptProvider().generate_script(source_markdown, episode_id)
        payload["episode"]["duration_sec"] = 12
        return payload
