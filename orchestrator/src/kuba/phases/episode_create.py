import unicodedata
from pathlib import Path

from kuba.state.episode_state import EpisodeState


EPISODE_DIRS = [
    "script",
    "logs",
    "audio/narration",
    "images/characters",
    "images/scenes",
    "images/fallback_stills",
    "video/motion",
    "render",
]


def create_episode(output_root: Path, title: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    episode_root = output_root / _slugify(title)
    episode_root.mkdir()

    for relative_dir in EPISODE_DIRS:
        (episode_root / relative_dir).mkdir(parents=True)

    (episode_root / "script" / "source.md").write_text(f"{title}\n", encoding="utf-8")
    EpisodeState.new().save(episode_root / "state.json")
    return episode_root


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    slug_parts: list[str] = []
    pending_separator = False

    for character in normalized:
        if unicodedata.combining(character):
            continue
        if character in {"'", "’"}:
            continue
        if character.isalnum():
            if pending_separator and slug_parts:
                slug_parts.append("-")
            slug_parts.append(character)
            pending_separator = False
        else:
            pending_separator = bool(slug_parts)

    slug = "".join(slug_parts).strip("-")
    if not slug:
        raise ValueError("episode title must contain at least one alphanumeric character")
    return slug
