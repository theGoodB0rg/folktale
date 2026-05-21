from pathlib import Path

from PIL import Image

from kuba.quality.visual_diversity import analyze_visual_diversity


def test_visual_diversity_flags_nearly_identical_scene_images(tmp_path: Path):
    paths = []
    for index in range(4):
        path = tmp_path / f"scene_{index}.png"
        Image.new("RGB", (64, 64), (20, 80, 120)).save(path)
        paths.append(path)

    report = analyze_visual_diversity(paths)

    assert report.ok is False
    assert any("too similar" in issue for issue in report.issues)


def test_visual_diversity_accepts_distinct_scene_images(tmp_path: Path):
    colors = [(20, 80, 120), (120, 30, 20), (30, 130, 50), (200, 180, 60)]
    paths = []
    for index, color in enumerate(colors):
        path = tmp_path / f"scene_{index}.png"
        Image.new("RGB", (64, 64), color).save(path)
        paths.append(path)

    report = analyze_visual_diversity(paths)

    assert report.ok is True
