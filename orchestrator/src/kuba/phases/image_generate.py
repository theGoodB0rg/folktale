from pathlib import Path

from kuba.blueprint.loader import load_blueprint
from kuba.planning.shot_plan import build_scene_prompt
from kuba.providers.base import ImageProvider
from kuba.state.episode_state import EpisodeState, Manifest, ManifestEntry, PhaseStatus


PHASE_NAME = "image_generate"


def generate_images(episode_root: Path, image_provider: ImageProvider) -> None:
    blueprint = load_blueprint(episode_root / "blueprint.json")
    manifest_path = episode_root / "images" / "manifest.json"
    manifest = _load_or_create_manifest(manifest_path)
    entries_by_asset_id = {entry.asset_id: entry for entry in manifest.entries}

    character_ref_map = {
        character.id: character.reference_image_path
        for character in blueprint.characters
    }

    for scene in blueprint.scenes:
        environment = scene.visual_prompt.get("environment", str(scene.visual_prompt))
        shot_kind = str(
            scene.visual_prompt.get(
                "shot_kind",
                scene.camera_motion.get("type", "wide_action"),
            )
        )
        seed_text = build_scene_prompt(
            beat=scene.beat,
            environment=environment,
            characters=list(scene.characters_present),
            shot_kind=shot_kind,
        )

        ref_path: str | None = None
        for character_id in scene.characters_present:
            path = character_ref_map.get(character_id)
            if path is not None:
                ref_path = path
                break

        image_provider.generate_image(
            str(episode_root),
            scene.asset_path,
            seed_text,
            reference_image_path=ref_path,
        )
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
