import json
from pathlib import Path

from kuba.blueprint.loader import load_blueprint
from kuba.media.audio_probe import probe_audio
from kuba.providers.base import AudioProvider
from kuba.state.episode_state import EpisodeState, PhaseStatus


PHASE_NAME = "audio_generate"


def generate_audio(episode_root: Path, audio_provider: AudioProvider) -> None:
    blueprint = load_blueprint(episode_root / "blueprint.json")
    manifest_path = episode_root / "audio" / "manifest.json"
    manifest = _load_manifest(manifest_path)
    entries_by_asset_id = {entry["asset_id"]: entry for entry in manifest["entries"]}

    for segment in blueprint.narration.segments:
        audio_provider.generate_audio(
            str(episode_root),
            segment.audio_path,
            segment.text,
            segment.target_duration_sec,
        )
        entry: dict[str, object] = {
            "asset_id": segment.id,
            "blueprint_ref": segment.id,
            "relative_path": segment.audio_path,
            "status": PhaseStatus.COMPLETED.value,
            "provider": audio_provider.provider_name,
        }
        probe = probe_audio(episode_root / segment.audio_path)
        if probe.duration_sec is not None:
            entry["duration_sec"] = probe.duration_sec
        entries_by_asset_id[segment.id] = entry

    manifest["entries"] = list(entries_by_asset_id.values())
    _save_manifest(manifest_path, manifest)

    state_path = episode_root / "state.json"
    state = EpisodeState.load(state_path)
    state.set_phase(PHASE_NAME, PhaseStatus.COMPLETED)
    state.save(state_path)


def _load_manifest(path: Path) -> dict[str, list[dict[str, object]]]:
    if not path.exists():
        return {"entries": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_manifest(path: Path, manifest: dict[str, list[dict[str, object]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
