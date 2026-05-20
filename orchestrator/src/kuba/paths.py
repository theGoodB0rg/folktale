from pathlib import Path, PureWindowsPath


def resolve_episode_path(episode_root: Path, relative_path: str) -> Path:
    path = Path(relative_path)
    windows_path = PureWindowsPath(relative_path)
    if path.is_absolute() or windows_path.drive or windows_path.root:
        raise ValueError("episode paths must be relative")

    root = episode_root.resolve()
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("episode path must not escape episode root") from exc

    return resolved
