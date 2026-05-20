from pathlib import Path

from kuba.phases.audio_generate import generate_audio
from kuba.phases.episode_create import create_episode
from kuba.phases.resume import resume_episode
from kuba.phases.script_generate import generate_script
from kuba.providers.fake import FakeAudioProvider, FakeImageProvider, FakeScriptProvider


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
