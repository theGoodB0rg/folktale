from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError


@dataclass(frozen=True)
class ImageProbeResult:
    exists: bool
    valid: bool
    width: int | None = None
    height: int | None = None
    error: str | None = None


def probe_image(path: Path) -> ImageProbeResult:
    if not path.exists():
        return ImageProbeResult(exists=False, valid=False, error="file does not exist")

    try:
        with Image.open(path) as image:
            width, height = image.size
            image.verify()
    except (OSError, UnidentifiedImageError) as exc:
        return ImageProbeResult(
            exists=True,
            valid=False,
            error=str(exc) or exc.__class__.__name__,
        )

    return ImageProbeResult(exists=True, valid=True, width=width, height=height)
