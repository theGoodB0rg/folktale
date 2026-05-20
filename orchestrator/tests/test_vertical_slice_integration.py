from pathlib import Path
import json

import pytest
from pydantic import ValidationError

from kuba.blueprint.loader import load_blueprint
from kuba.phases.audio_generate import generate_audio
from kuba.phases.character_refs import approve_refs, generate_refs
from kuba.phases.episode_create import create_episode
from kuba.phases.image_generate import generate_images
from kuba.phases.script_generate import generate_script
from kuba.phases.validate_assets import validate_assets
from kuba.phases.video_generate import generate_video
from kuba.providers.fake import (
    FakeAudioProvider,
    FakeImageProvider,
    FakeScriptProvider,
    FailingFakeVideoProvider,
)
from kuba.state.episode_state import EpisodeState, Manifest, PhaseStatus


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


def test_full_fake_asset_generation_uses_fallback_when_video_fails(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    generate_refs(episode_root, FakeImageProvider())
    approve_refs(episode_root)

    generate_audio(episode_root, FakeAudioProvider())
    generate_images(episode_root, FakeImageProvider())
    generate_video(episode_root, FailingFakeVideoProvider(), FakeImageProvider())
    report = validate_assets(episode_root, mode="dev")

    assert report.ok is True
    assert (episode_root / "images" / "fallback_stills" / "motion_0001_fallback.png").exists()
    state = EpisodeState.load(episode_root / "state.json")
    assert state.phases["validate_assets"] == PhaseStatus.COMPLETED


def test_production_validation_fails_when_motion_uses_fallback_still(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    generate_refs(episode_root, FakeImageProvider())
    approve_refs(episode_root)
    generate_audio(episode_root, FakeAudioProvider())
    generate_images(episode_root, FakeImageProvider())
    generate_video(episode_root, FailingFakeVideoProvider(), FakeImageProvider())

    report = validate_assets(episode_root, mode="production")

    assert report.ok is False
    assert any("real mp4" in error.lower() for error in report.errors)


def test_production_generation_fails_instead_of_falling_back_when_video_fails(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    generate_images(episode_root, FakeImageProvider())

    with pytest.raises(RuntimeError, match="production video generation failed"):
        generate_video(
            episode_root,
            FailingFakeVideoProvider(),
            FakeImageProvider(),
            mode="production",
        )

    assert not (episode_root / "images" / "fallback_stills" / "motion_0001_fallback.png").exists()
    state = EpisodeState.load(episode_root / "state.json")
    assert state.phases["video_generate"] == PhaseStatus.FAILED


def test_production_validation_fails_for_fake_provider_assets(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    generate_refs(episode_root, FakeImageProvider())
    approve_refs(episode_root)
    generate_audio(episode_root, FakeAudioProvider())
    generate_images(episode_root, FakeImageProvider())

    report = validate_assets(episode_root, mode="production")

    assert report.ok is False
    assert any("fake provider" in error.lower() for error in report.errors)


def test_validate_assets_fails_when_approved_character_ref_is_missing(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    generate_refs(episode_root, FakeImageProvider())
    approve_refs(episode_root)
    generate_audio(episode_root, FakeAudioProvider())
    generate_images(episode_root, FakeImageProvider())
    generate_video(episode_root, FailingFakeVideoProvider(), FakeImageProvider())
    (episode_root / "images" / "characters" / "protagonist_ref.png").unlink()

    report = validate_assets(episode_root)

    assert report.ok is False
    assert any("character reference protagonist" in error for error in report.errors)
    state = EpisodeState.load(episode_root / "state.json")
    assert state.phases["validate_assets"] == PhaseStatus.FAILED


def test_validate_assets_fails_when_required_still_scene_count_is_too_high(
    tmp_path: Path,
):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    blueprint_path = episode_root / "blueprint.json"
    payload = json.loads(blueprint_path.read_text(encoding="utf-8"))
    payload["validation"]["required_assets"]["still_scenes_min"] = 99
    blueprint_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    generate_refs(episode_root, FakeImageProvider())
    approve_refs(episode_root)
    generate_audio(episode_root, FakeAudioProvider())
    generate_images(episode_root, FakeImageProvider())
    generate_video(episode_root, FailingFakeVideoProvider(), FakeImageProvider())

    report = validate_assets(episode_root)

    assert report.ok is False
    assert any("still scene count" in error for error in report.errors)
    state = EpisodeState.load(episode_root / "state.json")
    assert state.phases["validate_assets"] == PhaseStatus.FAILED


def test_generate_images_preserves_existing_character_manifest_entries(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    generate_refs(episode_root, FakeImageProvider())

    generate_images(episode_root, FakeImageProvider())

    manifest = Manifest.load(episode_root / "images" / "manifest.json")
    assert manifest.by_asset_id("protagonist").relative_path == (
        "images/characters/protagonist_ref.png"
    )
    assert manifest.by_asset_id("river_spirit").relative_path == (
        "images/characters/river_spirit_ref.png"
    )
    assert manifest.by_asset_id("scene_0001").relative_path == "images/scenes/scene_0001.png"


def test_generate_images_creates_motion_source_scene_image(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())

    generate_images(episode_root, FakeImageProvider())

    assert (episode_root / "images" / "scenes" / "scene_0004.png").exists()
