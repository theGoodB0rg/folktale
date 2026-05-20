from dataclasses import dataclass
import json
from pathlib import Path
import subprocess


FFPROBE_TIMEOUT_SEC = 5


@dataclass(frozen=True)
class AudioProbeResult:
    exists: bool
    valid: bool
    duration_sec: float | None = None
    error: str | None = None


def probe_audio(path: Path) -> AudioProbeResult:
    if not path.exists():
        return AudioProbeResult(exists=False, valid=False, error="file does not exist")

    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=FFPROBE_TIMEOUT_SEC,
        )
        payload = json.loads(completed.stdout)
        duration = float(payload["format"]["duration"])
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        return AudioProbeResult(
            exists=True,
            valid=False,
            error=str(exc) or exc.__class__.__name__,
        )

    return AudioProbeResult(exists=True, valid=True, duration_sec=duration)
