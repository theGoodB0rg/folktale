from collections.abc import Callable
from pathlib import Path

from kuba.paths import resolve_episode_path
from kuba.state.episode_state import ManifestEntry, PhaseStatus


def should_skip_asset(
    episode_root: Path, entry: ManifestEntry, probe: Callable[[Path], bool]
) -> bool:
    if entry.status != PhaseStatus.COMPLETED:
        return False

    try:
        resolved_path = resolve_episode_path(episode_root, entry.relative_path)
    except ValueError:
        return False

    return resolved_path.exists() and probe(resolved_path)
