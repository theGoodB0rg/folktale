from dataclasses import dataclass
import json
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class VideoProbeResult:
    exists: bool
    valid: bool
    duration_sec: float | None = None
    width: int | None = None
    height: int | None = None
    has_audio: bool | None = None
    error: str | None = None


def probe_video(path: Path) -> VideoProbeResult:
    if not path.exists():
        return VideoProbeResult(exists=False, valid=False, error="file does not exist")

    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,width,height",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        duration = float(payload["format"]["duration"])
        streams = payload.get("streams", [])
        video_stream = next(
            stream for stream in streams if stream.get("codec_type") == "video"
        )
        width = int(video_stream["width"])
        height = int(video_stream["height"])
        has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        KeyError,
        StopIteration,
        TypeError,
        ValueError,
    ) as exc:
        return VideoProbeResult(
            exists=True,
            valid=False,
            error=str(exc) or exc.__class__.__name__,
        )

    return VideoProbeResult(
        exists=True,
        valid=True,
        duration_sec=duration,
        width=width,
        height=height,
        has_audio=has_audio,
    )
