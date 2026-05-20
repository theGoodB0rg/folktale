from pathlib import Path
import subprocess

from PIL import Image

from kuba.media.audio_probe import probe_audio
from kuba.media.image_probe import probe_image
from kuba.media.video_probe import probe_video


def test_probe_image_returns_dimensions(tmp_path: Path):
    path = tmp_path / "scene.png"
    Image.new("RGB", (1280, 720), color=(10, 20, 30)).save(path)

    info = probe_image(path)

    assert info.exists is True
    assert info.width == 1280
    assert info.height == 720
    assert info.valid is True


def test_probe_corrupt_image_is_invalid(tmp_path: Path):
    path = tmp_path / "scene.png"
    path.write_bytes(b"not an image")

    info = probe_image(path)

    assert info.exists is True
    assert info.valid is False
    assert info.width is None
    assert info.height is None
    assert info.error is not None


def test_probe_missing_audio_is_invalid(tmp_path: Path):
    info = probe_audio(tmp_path / "missing.wav")

    assert info.exists is False
    assert info.valid is False


def test_probe_audio_handles_missing_ffprobe(tmp_path: Path, monkeypatch):
    path = tmp_path / "tone.wav"
    path.write_bytes(b"not actually audio")

    def fail_ffprobe(*args, **kwargs):
        raise FileNotFoundError("ffprobe")

    monkeypatch.setattr(subprocess, "run", fail_ffprobe)

    info = probe_audio(path)

    assert info.exists is True
    assert info.valid is False
    assert info.duration_sec is None
    assert info.error is not None


def test_probe_missing_video_is_invalid(tmp_path: Path):
    info = probe_video(tmp_path / "missing.mp4")

    assert info.exists is False
    assert info.valid is False


def test_probe_video_handles_missing_ffprobe(tmp_path: Path, monkeypatch):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"not actually video")

    def fail_ffprobe(*args, **kwargs):
        raise FileNotFoundError("ffprobe")

    monkeypatch.setattr(subprocess, "run", fail_ffprobe)

    info = probe_video(path)

    assert info.exists is True
    assert info.valid is False
    assert info.duration_sec is None
    assert info.width is None
    assert info.height is None
    assert info.has_audio is None
    assert info.error is not None
