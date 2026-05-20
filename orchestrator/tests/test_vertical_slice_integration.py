from pathlib import Path

import pytest

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
