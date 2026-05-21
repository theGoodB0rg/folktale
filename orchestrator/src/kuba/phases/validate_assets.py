from dataclasses import dataclass, field
from pathlib import Path

from kuba.blueprint.loader import load_blueprint
from kuba.media.audio_probe import probe_audio
from kuba.media.image_probe import probe_image
from kuba.media.video_probe import probe_video
from kuba.mode import RunMode, is_fake_provider, normalize_mode
from kuba.paths import resolve_episode_path
from kuba.quality.story_timing import analyze_story_timing
from kuba.quality.visual_diversity import analyze_visual_diversity
from kuba.state.episode_state import EpisodeState, PhaseStatus


@dataclass(frozen=True)
class AssetValidationReport:
    ok: bool
    errors: list[str] = field(default_factory=list)


def validate_assets(episode_root: Path, *, mode: RunMode = "dev") -> AssetValidationReport:
    run_mode = normalize_mode(mode)
    blueprint = load_blueprint(episode_root / "blueprint.json")
    errors: list[str] = []
    required = blueprint.validation.required_assets

    character_count = len(blueprint.characters)
    if character_count < required.character_refs:
        errors.append(
            f"character reference count {character_count} is below required "
            f"{required.character_refs}"
        )

    still_scene_count = sum(1 for scene in blueprint.scenes if scene.type == "still")
    if still_scene_count < required.still_scenes_min:
        errors.append(
            f"still scene count {still_scene_count} is below required "
            f"{required.still_scenes_min}"
        )

    motion_shot_count = len(blueprint.motion_shots)
    if motion_shot_count < required.motion_shots:
        errors.append(
            f"motion shot count {motion_shot_count} is below required "
            f"{required.motion_shots}"
        )

    narration_count = len(blueprint.narration.segments)
    if narration_count < required.narration_segments_min:
        errors.append(
            f"narration segment count {narration_count} is below required "
            f"{required.narration_segments_min}"
        )

    audio_durations_by_asset_id: dict[str, float] = {}
    for segment in blueprint.narration.segments:
        path = resolve_episode_path(episode_root, segment.audio_path)
        result = probe_audio(path)
        if not result.valid:
            errors.append(
                f"narration segment {segment.id} invalid at {segment.audio_path}: "
                f"{result.error or 'invalid audio'}"
            )
        elif result.duration_sec is not None:
            audio_durations_by_asset_id[segment.id] = result.duration_sec

    for character in blueprint.characters:
        path = resolve_episode_path(episode_root, character.reference_image_path)
        result = probe_image(path)
        if not result.valid:
            errors.append(
                f"character reference {character.id} invalid at "
                f"{character.reference_image_path}: {result.error or 'invalid image'}"
            )

    for scene in blueprint.scenes:
        path = resolve_episode_path(episode_root, scene.asset_path)
        result = probe_image(path)
        if not result.valid:
            errors.append(
                f"scene {scene.id} invalid at {scene.asset_path}: "
                f"{result.error or 'invalid image'}"
            )

    for shot in blueprint.motion_shots:
        video_path = resolve_episode_path(episode_root, shot.asset_path)
        video_result = probe_video(video_path)
        if video_result.valid:
            continue
        if run_mode == "production":
            errors.append(
                f"motion shot {shot.id} requires a real MP4 motion asset in production: "
                f"{video_result.error or 'invalid video'}"
            )
            continue
        fallback_path = resolve_episode_path(episode_root, shot.fallback_asset_path)
        fallback_result = probe_image(fallback_path)
        if not fallback_result.valid:
            errors.append(
                f"motion shot {shot.id} requires valid video or fallback still: "
                f"video={video_result.error or 'invalid video'}; "
                f"fallback={fallback_result.error or 'invalid image'}"
            )

    if run_mode == "production":
        scene_paths = [
            resolve_episode_path(episode_root, scene.asset_path)
            for scene in blueprint.scenes
        ]
        visual_report = analyze_visual_diversity(scene_paths)
        errors.extend(visual_report.issues)
        timing_report = analyze_story_timing(
            {
                "episode_duration_sec": blueprint.episode.duration_sec,
                "narration": [
                    {
                        "id": segment.id,
                        "start_sec": segment.start_sec,
                        "target_duration_sec": segment.target_duration_sec,
                        "actual_duration_sec": audio_durations_by_asset_id.get(
                            segment.id,
                            segment.target_duration_sec,
                        ),
                    }
                    for segment in blueprint.narration.segments
                ],
                "scenes": [
                    {
                        "id": scene.id,
                        "start_sec": scene.start_sec,
                        "end_sec": scene.end_sec,
                        "type": scene.type,
                    }
                    for scene in blueprint.scenes
                ],
                "motion": [{"id": shot.id} for shot in blueprint.motion_shots],
            }
        )
        errors.extend(timing_report.issues)
        errors.extend(_fake_provider_errors(episode_root))

    report = AssetValidationReport(ok=not errors, errors=errors)
    state_path = episode_root / "state.json"
    state = EpisodeState.load(state_path)
    state.set_phase(
        "validate_assets",
        PhaseStatus.COMPLETED if report.ok else PhaseStatus.FAILED,
    )
    state.save(state_path)
    return report


def _fake_provider_errors(episode_root: Path) -> list[str]:
    errors: list[str] = []
    for manifest_path in [
        episode_root / "audio" / "manifest.json",
        episode_root / "images" / "manifest.json",
    ]:
        if not manifest_path.exists():
            continue
        import json

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest.get("entries", []):
            provider = str(entry.get("provider", ""))
            if is_fake_provider(provider):
                errors.append(
                    f"fake provider asset is not allowed in production: "
                    f"{entry.get('asset_id')} from {provider}"
                )

    video_manifest_path = episode_root / "video" / "manifest.json"
    if video_manifest_path.exists():
        import json

        manifest = json.loads(video_manifest_path.read_text(encoding="utf-8"))
        for entry in manifest.get("entries", []):
            provider = str(entry.get("provider", ""))
            status = str(entry.get("status", ""))
            if is_fake_provider(provider):
                errors.append(
                    f"fake provider asset is not allowed in production: "
                    f"{entry.get('asset_id')} from {provider}"
                )
            if status == PhaseStatus.FALLBACK_USED.value:
                errors.append(
                    f"fallback video asset is not allowed in production: "
                    f"{entry.get('asset_id')}"
                )
    return errors
