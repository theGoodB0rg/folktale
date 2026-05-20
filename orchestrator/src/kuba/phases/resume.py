import json
from pathlib import Path

from kuba.blueprint.loader import load_blueprint
from kuba.blueprint.schema import Blueprint
from kuba.media.audio_probe import probe_audio
from kuba.media.image_probe import probe_image
from kuba.media.video_probe import probe_video
from kuba.paths import resolve_episode_path
from kuba.phases.video_generate import generate_video
from kuba.providers.base import AudioProvider, ImageProvider, VideoProvider
from kuba.state.episode_state import Manifest, PhaseStatus


def resume_episode(
    episode_root: Path,
    audio_provider: AudioProvider,
    image_provider: ImageProvider,
    video_provider: VideoProvider | None = None,
) -> None:
    blueprint = load_blueprint(episode_root / "blueprint.json")
    audio_manifest_path = episode_root / "audio" / "manifest.json"
    audio_manifest = _load_json_manifest(audio_manifest_path)
    completed_audio_ids = {
        entry["asset_id"]
        for entry in audio_manifest["entries"]
        if entry.get("status") == PhaseStatus.COMPLETED.value
    }

    for segment in blueprint.narration.segments:
        if segment.id not in completed_audio_ids:
            continue
        result = probe_audio(resolve_episode_path(episode_root, segment.audio_path))
        if result.valid:
            continue
        audio_provider.generate_audio(
            str(episode_root),
            segment.audio_path,
            segment.text,
            segment.target_duration_sec,
        )

    image_manifest_path = episode_root / "images" / "manifest.json"
    required_image_paths = _required_image_paths_by_ref(blueprint)
    if image_manifest_path.exists():
        image_manifest = Manifest.load(image_manifest_path)
        completed_entries = [
            entry
            for entry in image_manifest.entries
            if entry.status in {PhaseStatus.COMPLETED, PhaseStatus.FALLBACK_USED}
        ]
    else:
        completed_entries = []

    for entry in completed_entries:
        expected_path = required_image_paths.get(entry.blueprint_ref)
        if expected_path is None or entry.relative_path != expected_path:
            continue
        try:
            resolved_path = resolve_episode_path(episode_root, entry.relative_path)
        except ValueError:
            continue
        result = probe_image(resolved_path)
        if result.valid:
            continue
        image_provider.generate_image(
            str(episode_root),
            entry.relative_path,
            f"{entry.blueprint_ref} resumed",
        )

    if video_provider is None:
        return

    video_manifest_path = episode_root / "video" / "manifest.json"
    video_manifest = _load_json_manifest(video_manifest_path)
    motion_shots_by_id = {shot.id: shot for shot in blueprint.motion_shots}
    for entry in video_manifest["entries"]:
        if entry.get("status") != PhaseStatus.COMPLETED.value:
            continue
        shot = motion_shots_by_id.get(
            str(entry.get("blueprint_ref") or entry.get("asset_id"))
        )
        if shot is None or entry.get("relative_path") != shot.asset_path:
            continue
        try:
            resolved_path = resolve_episode_path(episode_root, shot.asset_path)
        except ValueError:
            continue
        if probe_video(resolved_path).valid:
            continue
        generate_video(episode_root, video_provider, image_provider)
        break


def _load_json_manifest(path: Path) -> dict[str, list[dict[str, object]]]:
    if not path.exists():
        return {"entries": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _required_image_paths_by_ref(blueprint: Blueprint) -> dict[str, str]:
    paths = {
        character.id: character.reference_image_path
        for character in blueprint.characters
    }
    paths.update(
        {
            scene.id: scene.asset_path
            for scene in blueprint.scenes
            if scene.type == "still"
        }
    )
    paths.update(
        {
            shot.id: shot.fallback_asset_path
            for shot in blueprint.motion_shots
        }
    )
    return paths
