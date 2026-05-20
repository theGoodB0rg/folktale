from pathlib import Path

from kuba.blueprint.loader import load_blueprint
from kuba.providers.base import ImageProvider
from kuba.state.episode_state import EpisodeState, Manifest, ManifestEntry, PhaseStatus


PHASE_NAME = "image_generate"


def generate_images(episode_root: Path, image_provider: ImageProvider) -> None:
    blueprint = load_blueprint(episode_root / "blueprint.json")
    manifest_path = episode_root / "images" / "manifest.json"
    manifest = _load_or_create_manifest(manifest_path)
    entries_by_asset_id = {entry.asset_id: entry for entry in manifest.entries}

    for scene in blueprint.scenes:
        if scene.type != "still":
            continue
        seed_text = f"{scene.beat} {scene.visual_prompt}"
        image_provider.generate_image(str(episode_root), scene.asset_path, seed_text)
        entries_by_asset_id[scene.id] = ManifestEntry(
            asset_id=scene.id,
            blueprint_ref=scene.id,
            relative_path=scene.asset_path,
            status=PhaseStatus.COMPLETED,
            provider=image_provider.provider_name,
        )

    manifest.entries = list(entries_by_asset_id.values())
    manifest.save(manifest_path)

    state_path = episode_root / "state.json"
    state = EpisodeState.load(state_path)
    state.set_phase(PHASE_NAME, PhaseStatus.COMPLETED)
    state.save(state_path)


def _load_or_create_manifest(path: Path) -> Manifest:
    if path.exists():
        return Manifest.load(path)
    return Manifest()
