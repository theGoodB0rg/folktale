import json
from pathlib import Path

from kuba.blueprint.loader import load_blueprint
from kuba.media.audio_probe import probe_audio
from kuba.media.image_probe import probe_image
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
        result = probe_audio(episode_root / segment.audio_path)
        if result.valid:
            continue
        audio_provider.generate_audio(
            str(episode_root),
            segment.audio_path,
            segment.text,
            segment.target_duration_sec,
        )

    image_manifest_path = episode_root / "images" / "manifest.json"
    if not image_manifest_path.exists():
        return

    image_manifest = Manifest.load(image_manifest_path)
    completed_entries = [
        entry
        for entry in image_manifest.entries
        if entry.status in {PhaseStatus.COMPLETED, PhaseStatus.FALLBACK_USED}
    ]
    for entry in completed_entries:
        result = probe_image(episode_root / entry.relative_path)
        if result.valid:
            continue
        image_provider.generate_image(
            str(episode_root),
            entry.relative_path,
            f"{entry.blueprint_ref} resumed",
        )


def _load_json_manifest(path: Path) -> dict[str, list[dict[str, object]]]:
    if not path.exists():
        return {"entries": []}
    return json.loads(path.read_text(encoding="utf-8"))
