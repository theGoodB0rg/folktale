from pathlib import Path

import pytest

from kuba.paths import resolve_episode_path


def test_resolve_episode_path_returns_resolved_path(tmp_path: Path):
    episode = tmp_path / "episodes" / "river-debt"
    episode.mkdir(parents=True)

    resolved = resolve_episode_path(episode, "images/scenes/scene_0001.png")

    assert resolved == episode.resolve() / "images" / "scenes" / "scene_0001.png"


def test_resolve_episode_path_rejects_absolute_path(tmp_path: Path):
    episode = tmp_path / "episodes" / "river-debt"
    episode.mkdir(parents=True)

    with pytest.raises(ValueError, match="relative"):
        resolve_episode_path(episode, "C:/outside/file.png")


@pytest.mark.parametrize(
    "path",
    [
        r"C:outside\file.png",
        r"D:outside\file.png",
        r"\outside\file.png",
        r"\\server\share\file.png",
    ],
)
def test_resolve_episode_path_rejects_windows_drive_root_and_unc_paths(
    tmp_path: Path, path: str
):
    episode = tmp_path / "episodes" / "river-debt"
    episode.mkdir(parents=True)

    with pytest.raises(ValueError, match="relative"):
        resolve_episode_path(episode, path)


def test_resolve_episode_path_rejects_parent_escape(tmp_path: Path):
    episode = tmp_path / "episodes" / "river-debt"
    episode.mkdir(parents=True)

    with pytest.raises(ValueError, match="escape"):
        resolve_episode_path(episode, "../outside/file.png")
