from dataclasses import dataclass, field
from pathlib import Path

from kuba.blueprint.loader import load_blueprint
from kuba.media.audio_probe import probe_audio
from kuba.media.image_probe import probe_image
from kuba.media.video_probe import probe_video
from kuba.paths import resolve_episode_path
from kuba.state.episode_state import EpisodeState, PhaseStatus


@dataclass(frozen=True)
class AssetValidationReport:
    ok: bool
    errors: list[str] = field(default_factory=list)


def validate_assets(episode_root: Path) -> AssetValidationReport:
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

    for segment in blueprint.narration.segments:
        path = resolve_episode_path(episode_root, segment.audio_path)
        result = probe_audio(path)
        if not result.valid:
            errors.append(
                f"narration segment {segment.id} invalid at {segment.audio_path}: "
                f"{result.error or 'invalid audio'}"
            )

    for character in blueprint.characters:
        path = resolve_episode_path(episode_root, character.reference_image_path)
        result = probe_image(path)
        if not result.valid:
            errors.append(
                f"character reference {character.id} invalid at "
                f"{character.reference_image_path}: {result.error or 'invalid image'}"
            )

    for scene in blueprint.scenes:
        if scene.type != "still":
            continue
        path = resolve_episode_path(episode_root, scene.asset_path)
        result = probe_image(path)
        if not result.valid:
            errors.append(
                f"still scene {scene.id} invalid at {scene.asset_path}: "
                f"{result.error or 'invalid image'}"
            )

    for shot in blueprint.motion_shots:
        video_path = resolve_episode_path(episode_root, shot.asset_path)
        video_result = probe_video(video_path)
        if video_result.valid:
            continue
        fallback_path = resolve_episode_path(episode_root, shot.fallback_asset_path)
        fallback_result = probe_image(fallback_path)
        if not fallback_result.valid:
            errors.append(
                f"motion shot {shot.id} requires valid video or fallback still: "
                f"video={video_result.error or 'invalid video'}; "
                f"fallback={fallback_result.error or 'invalid image'}"
            )

    report = AssetValidationReport(ok=not errors, errors=errors)
    state_path = episode_root / "state.json"
    state = EpisodeState.load(state_path)
    state.set_phase(
        "validate_assets",
        PhaseStatus.COMPLETED if report.ok else PhaseStatus.FAILED,
    )
    state.save(state_path)
    return report
