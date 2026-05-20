from pathlib import Path

from kuba.blueprint.loader import load_blueprint
from kuba.media.image_probe import probe_image
from kuba.paths import resolve_episode_path
from kuba.providers.base import ImageProvider
from kuba.state.episode_state import EpisodeState, Manifest, ManifestEntry, PhaseStatus


PHASE_NAME = "character_refs"


def generate_refs(episode_root: Path, image_provider: ImageProvider) -> list[Path]:
    blueprint = load_blueprint(episode_root / "blueprint.json")
    generated_paths: list[Path] = []

    manifest_path = episode_root / "images" / "manifest.json"
    manifest = _load_or_create_manifest(manifest_path)
    entries_by_asset_id = {entry.asset_id: entry for entry in manifest.entries}

    for character in blueprint.characters:
        seed_text = f"{character.display_name} {character.identity_prompt}"
        generated_path = Path(
            image_provider.generate_image(
                str(episode_root),
                character.reference_image_path,
                seed_text,
            )
        )
        generated_paths.append(generated_path)
        entries_by_asset_id[character.id] = ManifestEntry(
            asset_id=character.id,
            blueprint_ref=character.id,
            relative_path=character.reference_image_path,
            status=PhaseStatus.COMPLETED,
            provider=image_provider.provider_name,
        )

    manifest.entries = list(entries_by_asset_id.values())
    manifest.save(manifest_path)

    state_path = episode_root / "state.json"
    state = EpisodeState.load(state_path)
    state.set_phase(PHASE_NAME, PhaseStatus.WAITING_FOR_REVIEW)
    state.save(state_path)

    return generated_paths


def approve_refs(episode_root: Path) -> None:
    blueprint = load_blueprint(episode_root / "blueprint.json")

    for character in blueprint.characters:
        reference_path = resolve_episode_path(episode_root, character.reference_image_path)
        result = probe_image(reference_path)
        if not result.valid:
            detail = result.error or "invalid image"
            raise ValueError(
                "character reference "
                f"{character.id} is missing or invalid at "
                f"{character.reference_image_path}: {detail}"
            )

    state_path = episode_root / "state.json"
    state = EpisodeState.load(state_path)
    state.set_phase(PHASE_NAME, PhaseStatus.COMPLETED)
    state.save(state_path)


def _load_or_create_manifest(path: Path) -> Manifest:
    if path.exists():
        return Manifest.load(path)
    return Manifest()
