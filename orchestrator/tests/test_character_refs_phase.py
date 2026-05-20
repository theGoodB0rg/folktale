from pathlib import Path

import pytest

from kuba.phases.character_refs import approve_refs, generate_refs
from kuba.phases.episode_create import create_episode
from kuba.phases.script_generate import generate_script
from kuba.providers.fake import FakeImageProvider, FakeScriptProvider
from kuba.state.episode_state import EpisodeState, Manifest, PhaseStatus


def prepared_episode(tmp_path: Path) -> Path:
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    return episode_root


def test_generate_refs_writes_character_images_and_waits_for_review(tmp_path: Path):
    episode_root = prepared_episode(tmp_path)
    generated = generate_refs(episode_root, FakeImageProvider())
    assert len(generated) == 2
    assert (episode_root / "images" / "characters" / "protagonist_ref.png").exists()
    manifest = Manifest.load(episode_root / "images" / "manifest.json")
    assert manifest.by_asset_id("protagonist").status == "completed"
    state = EpisodeState.load(episode_root / "state.json")
    assert state.phases["character_refs"] == PhaseStatus.WAITING_FOR_REVIEW


def test_approve_refs_marks_phase_completed(tmp_path: Path):
    episode_root = prepared_episode(tmp_path)
    generate_refs(episode_root, FakeImageProvider())
    approve_refs(episode_root)
    state = EpisodeState.load(episode_root / "state.json")
    assert state.phases["character_refs"] == PhaseStatus.COMPLETED


def test_approve_refs_rejects_missing_reference(tmp_path: Path):
    episode_root = prepared_episode(tmp_path)
    generate_refs(episode_root, FakeImageProvider())
    (episode_root / "images" / "characters" / "protagonist_ref.png").unlink()
    with pytest.raises(ValueError, match="character reference"):
        approve_refs(episode_root)
    state = EpisodeState.load(episode_root / "state.json")
    assert state.phases["character_refs"] == PhaseStatus.WAITING_FOR_REVIEW


def test_approve_refs_rejects_invalid_reference(tmp_path: Path):
    episode_root = prepared_episode(tmp_path)
    generate_refs(episode_root, FakeImageProvider())
    (episode_root / "images" / "characters" / "protagonist_ref.png").write_text(
        "not an image",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="character reference"):
        approve_refs(episode_root)
    state = EpisodeState.load(episode_root / "state.json")
    assert state.phases["character_refs"] == PhaseStatus.WAITING_FOR_REVIEW
