from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from kuba.paths import resolve_episode_path


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Episode(StrictModel):
    id: str
    title: str
    duration_sec: float
    format: str

    @field_validator("duration_sec")
    @classmethod
    def validate_vertical_slice_duration(cls, value: float) -> float:
        if not 60 <= value <= 90:
            raise ValueError("episode duration must be 60-90 seconds inclusive")
        return value


class RenderSize(StrictModel):
    width: int
    height: int


class RenderAudio(StrictModel):
    mode: str
    normalize: bool


class Render(StrictModel):
    fps: int
    preview: RenderSize
    final: RenderSize
    audio: RenderAudio


class Style(StrictModel):
    visual_style: str
    palette: str
    negative_prompt: str


BLUEPRINT_PATH_ROOT = Path("__episode__")


def validate_relative_blueprint_path(value: str) -> str:
    resolve_episode_path(BLUEPRINT_PATH_ROOT, value)
    return value


class Character(StrictModel):
    id: str
    role: str
    display_name: str
    consistency_scope: str
    reference_image_path: str
    identity_lock: dict[str, Any]
    identity_prompt: dict[str, Any]
    flexibility: dict[str, Any]

    _validate_reference_image_path = field_validator("reference_image_path")(
        validate_relative_blueprint_path
    )


class NarrationSegment(StrictModel):
    id: str
    scene_id: str
    text: str
    start_sec: float
    target_duration_sec: float
    audio_path: str

    _validate_audio_path = field_validator("audio_path")(validate_relative_blueprint_path)


class Narration(StrictModel):
    voice_profile: str
    segments: list[NarrationSegment]

    _validate_voice_profile = field_validator("voice_profile")(validate_relative_blueprint_path)


class Scene(StrictModel):
    id: str
    type: str
    start_sec: float
    end_sec: float
    beat: str
    characters_present: list[str]
    identity_lock: dict[str, Any]
    visual_prompt: dict[str, Any]
    asset_path: str
    camera_motion: dict[str, Any]
    transition_out: str

    _validate_asset_path = field_validator("asset_path")(validate_relative_blueprint_path)

    @model_validator(mode="after")
    def validate_timing(self) -> "Scene":
        if self.end_sec <= self.start_sec:
            raise ValueError("scene end_sec must be greater than start_sec")
        return self


class MotionShot(StrictModel):
    id: str
    scene_id: str
    provider: str
    duration_sec: float
    prompt: str
    source_image_path: str
    asset_path: str
    fallback_asset_path: str
    audio_policy: str

    _validate_source_image_path = field_validator("source_image_path")(
        validate_relative_blueprint_path
    )
    _validate_asset_path = field_validator("asset_path")(validate_relative_blueprint_path)
    _validate_fallback_asset_path = field_validator("fallback_asset_path")(
        validate_relative_blueprint_path
    )


class ValidationRequiredAssets(StrictModel):
    character_refs: int
    still_scenes_min: int
    motion_shots: int
    narration_segments_min: int


class Validation(StrictModel):
    require_character_review: bool
    required_assets: ValidationRequiredAssets


class Blueprint(StrictModel):
    schema_version: Literal["0.1"]
    episode: Episode
    render: Render
    style: Style
    characters: list[Character] = Field(min_length=1)
    narration: Narration
    scenes: list[Scene] = Field(min_length=1)
    motion_shots: list[MotionShot]
    validation: Validation

    @model_validator(mode="after")
    def validate_references(self) -> "Blueprint":
        _reject_duplicate_ids("characters", [character.id for character in self.characters])
        _reject_duplicate_ids("scenes", [scene.id for scene in self.scenes])
        _reject_duplicate_ids(
            "narration segments", [segment.id for segment in self.narration.segments]
        )
        _reject_duplicate_ids("motion_shots", [shot.id for shot in self.motion_shots])

        character_ids = {character.id for character in self.characters}
        scene_ids = {scene.id for scene in self.scenes}

        for scene in self.scenes:
            for character_id in scene.characters_present:
                if character_id not in character_ids:
                    raise ValueError(f"unknown character referenced by scene: {character_id}")

        for segment in self.narration.segments:
            if segment.scene_id not in scene_ids:
                raise ValueError(f"unknown scene referenced by narration segment: {segment.scene_id}")

        for shot in self.motion_shots:
            if shot.scene_id not in scene_ids:
                raise ValueError(f"unknown scene referenced by motion shot: {shot.scene_id}")

        return self


def _reject_duplicate_ids(label: str, ids: list[str]) -> None:
    seen: set[str] = set()
    for item_id in ids:
        if item_id in seen:
            raise ValueError(f"duplicate {label} id: {item_id}")
        seen.add(item_id)
