import json
from pathlib import Path

from kuba.blueprint.loader import load_blueprint
from kuba.media.video_probe import probe_video
from kuba.mode import RunMode, is_fake_provider, normalize_mode
from kuba.providers.base import ImageProvider, VideoProvider
from kuba.state.episode_state import EpisodeState, Manifest, ManifestEntry, PhaseStatus


PHASE_NAME = "video_generate"


def generate_video(
    episode_root: Path,
    video_provider: VideoProvider,
    fallback_image_provider: ImageProvider,
    *,
    mode: RunMode = "dev",
) -> None:
    run_mode = normalize_mode(mode)
    if run_mode == "production" and is_fake_provider(video_provider.provider_name):
        _fail_phase(episode_root)
        raise RuntimeError(
            "production video generation failed: fake video providers are disabled "
            "in production mode"
        )

    blueprint = load_blueprint(episode_root / "blueprint.json")
    video_manifest_path = episode_root / "video" / "manifest.json"
    video_manifest = _load_json_manifest(video_manifest_path)
    video_entries_by_asset_id = {
        entry["asset_id"]: entry for entry in video_manifest["entries"]
    }

    image_manifest_path = episode_root / "images" / "manifest.json"
    image_manifest = _load_or_create_image_manifest(image_manifest_path)
    image_entries_by_asset_id = {entry.asset_id: entry for entry in image_manifest.entries}

    fallback_used = False
    for shot in blueprint.motion_shots:
        try:
            video_provider.generate_video(
                str(episode_root),
                shot.asset_path,
                shot.source_image_path,
                shot.prompt,
                shot.duration_sec,
            )
            entry: dict[str, object] = {
                "asset_id": shot.id,
                "blueprint_ref": shot.id,
                "relative_path": shot.asset_path,
                "status": PhaseStatus.COMPLETED.value,
                "provider": video_provider.provider_name,
            }
            probe = probe_video(episode_root / shot.asset_path)
            if probe.duration_sec is not None:
                entry["duration_sec"] = probe.duration_sec
        except Exception as exc:
            if run_mode == "production":
                video_entries_by_asset_id[shot.id] = {
                    "asset_id": shot.id,
                    "blueprint_ref": shot.id,
                    "relative_path": shot.asset_path,
                    "status": PhaseStatus.FAILED.value,
                    "provider": video_provider.provider_name,
                    "error": str(exc),
                }
                video_manifest["entries"] = list(video_entries_by_asset_id.values())
                _save_json_manifest(video_manifest_path, video_manifest)
                _fail_phase(episode_root)
                raise RuntimeError(
                    f"production video generation failed for {shot.id}: {exc}"
                ) from exc
            fallback_used = True
            fallback_image_provider.generate_image(
                str(episode_root),
                shot.fallback_asset_path,
                f"{shot.prompt} fallback still",
            )
            entry = {
                "asset_id": shot.id,
                "blueprint_ref": shot.id,
                "relative_path": shot.asset_path,
                "status": PhaseStatus.FALLBACK_USED.value,
                "provider": video_provider.provider_name,
                "fallback_relative_path": shot.fallback_asset_path,
                "error": str(exc),
            }
            image_entries_by_asset_id[f"{shot.id}_fallback"] = ManifestEntry(
                asset_id=f"{shot.id}_fallback",
                blueprint_ref=shot.id,
                relative_path=shot.fallback_asset_path,
                status=PhaseStatus.FALLBACK_USED,
                provider=fallback_image_provider.provider_name,
            )
        video_entries_by_asset_id[shot.id] = entry

    video_manifest["entries"] = list(video_entries_by_asset_id.values())
    _save_json_manifest(video_manifest_path, video_manifest)
    image_manifest.entries = list(image_entries_by_asset_id.values())
    image_manifest.save(image_manifest_path)

    state_path = episode_root / "state.json"
    state = EpisodeState.load(state_path)
    state.set_phase(
        PHASE_NAME,
        PhaseStatus.FALLBACK_USED if fallback_used else PhaseStatus.COMPLETED,
    )
    state.save(state_path)


def _load_json_manifest(path: Path) -> dict[str, list[dict[str, object]]]:
    if not path.exists():
        return {"entries": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json_manifest(path: Path, manifest: dict[str, list[dict[str, object]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _load_or_create_image_manifest(path: Path) -> Manifest:
    if path.exists():
        return Manifest.load(path)
    return Manifest()


def _fail_phase(episode_root: Path) -> None:
    state_path = episode_root / "state.json"
    state = EpisodeState.load(state_path)
    state.set_phase(PHASE_NAME, PhaseStatus.FAILED)
    state.save(state_path)
