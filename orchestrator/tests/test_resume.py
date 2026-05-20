from pathlib import Path

from kuba.phases.audio_generate import generate_audio
from kuba.phases.character_refs import approve_refs, generate_refs
from kuba.phases.episode_create import create_episode
from kuba.phases.image_generate import generate_images
from kuba.phases.resume import resume_episode
from kuba.phases.script_generate import generate_script
from kuba.phases.validate_assets import validate_assets
from kuba.providers.fake import (
    FakeAudioProvider,
    FakeImageProvider,
    FakeScriptProvider,
    FailingFakeVideoProvider,
)
from kuba.state.episode_state import Manifest, ManifestEntry, PhaseStatus


def test_resume_regenerates_missing_completed_audio(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    generate_audio(episode_root, FakeAudioProvider())
    missing = episode_root / "audio" / "narration" / "seg_0001.wav"
    missing.unlink()

    resume_episode(
        episode_root,
        audio_provider=FakeAudioProvider(),
        image_provider=FakeImageProvider(),
    )

    assert missing.exists()


def test_resume_regenerates_corrupt_completed_scene_image(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    generate_images(episode_root, FakeImageProvider())
    corrupt = episode_root / "images" / "scenes" / "scene_0001.png"
    corrupt.write_text("not an image", encoding="utf-8")

    resume_episode(
        episode_root,
        audio_provider=FakeAudioProvider(),
        image_provider=FakeImageProvider(),
    )

    assert corrupt.read_bytes().startswith(b"\x89PNG")


def test_resume_ignores_manifest_path_escape(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    generate_images(episode_root, FakeImageProvider())
    outside = episode_root.parent / "escape.png"
    manifest = Manifest.load(episode_root / "images" / "manifest.json")
    manifest.entries.append(
        ManifestEntry(
            asset_id="escape",
            blueprint_ref="scene_0001",
            relative_path="../escape.png",
            status=PhaseStatus.COMPLETED,
            provider="fake",
        )
    )
    manifest.save(episode_root / "images" / "manifest.json")

    resume_episode(
        episode_root,
        audio_provider=FakeAudioProvider(),
        image_provider=FakeImageProvider(),
    )

    assert not outside.exists()


def test_resume_missing_completed_video_uses_fallback(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    generate_refs(episode_root, FakeImageProvider())
    approve_refs(episode_root)
    generate_audio(episode_root, FakeAudioProvider())
    generate_images(episode_root, FakeImageProvider())
    video_manifest_path = episode_root / "video" / "manifest.json"
    video_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    video_manifest_path.write_text(
        """
{
  "entries": [
    {
      "asset_id": "motion_0001",
      "blueprint_ref": "motion_0001",
      "relative_path": "video/motion/motion_0001.mp4",
      "status": "completed",
      "provider": "fake"
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    resume_episode(
        episode_root,
        audio_provider=FakeAudioProvider(),
        image_provider=FakeImageProvider(),
        video_provider=FailingFakeVideoProvider(),
    )

    assert (episode_root / "images" / "fallback_stills" / "motion_0001_fallback.png").exists()
    assert validate_assets(episode_root).ok is True
