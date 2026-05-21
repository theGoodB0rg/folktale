from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageStat


@dataclass(frozen=True)
class VisualDiversityReport:
    ok: bool
    issues: list[str]
    average_pair_distance: float


def analyze_visual_diversity(paths: list[Path]) -> VisualDiversityReport:
    signatures = [_signature(path) for path in paths]
    distances: list[float] = []
    for left_index, left in enumerate(signatures):
        for right in signatures[left_index + 1 :]:
            distances.append(_distance(left, right))

    average = sum(distances) / len(distances) if distances else 0.0
    issues: list[str] = []
    if len(paths) >= 4 and average < 18.0:
        issues.append(
            f"scene images are too similar: average thumbnail distance {average:.2f}"
        )
    return VisualDiversityReport(
        ok=not issues,
        issues=issues,
        average_pair_distance=average,
    )


def _signature(path: Path) -> tuple[float, float, float]:
    image = Image.open(path).convert("RGB").resize((16, 16))
    stat = ImageStat.Stat(image)
    return tuple(float(value) for value in stat.mean[:3])


def _distance(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return sum(abs(a - b) for a, b in zip(left, right)) / 3.0
