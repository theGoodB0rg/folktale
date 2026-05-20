import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from kuba.blueprint.loader import load_blueprint
from kuba.blueprint.schema import Blueprint
from kuba.blueprint.validator import validate_blueprint_file


def valid_blueprint_dict():
    return {
        "schema_version": "0.1",
        "episode": {
            "id": "river-debt",
            "title": "River Debt",
            "duration_sec": 72,
            "format": "youtube_landscape",
        },
        "render": {
            "fps": 30,
            "preview": {"width": 1280, "height": 720},
            "final": {"width": 1920, "height": 1080},
            "audio": {"mode": "narration_only", "normalize": True},
        },
        "style": {
            "visual_style": "cinematic African folktale anthology",
            "palette": "earth tones",
            "negative_prompt": "watermark, text",
        },
        "characters": [
            {
                "id": "protagonist",
                "role": "main",
                "display_name": "Amina",
                "consistency_scope": "episode",
                "reference_image_path": "images/characters/protagonist_ref.png",
                "identity_lock": {"priority": "strict", "face": "required"},
                "identity_prompt": {"age": "young adult"},
                "flexibility": {"pose": "flexible"},
            },
            {
                "id": "elder",
                "role": "elder",
                "display_name": "Baba",
                "consistency_scope": "episode",
                "reference_image_path": "images/characters/elder_ref.png",
                "identity_lock": {"priority": "strict", "face": "required"},
                "identity_prompt": {"age": "old man"},
                "flexibility": {"pose": "flexible"},
            },
        ],
        "narration": {
            "voice_profile": "config/voices/narrator.yaml",
            "segments": [
                {
                    "id": "seg_0001",
                    "scene_id": "scene_0001",
                    "text": "The river called her name.",
                    "start_sec": 0,
                    "target_duration_sec": 10,
                    "audio_path": "audio/narration/seg_0001.wav",
                }
            ],
        },
        "scenes": [
            {
                "id": "scene_0001",
                "type": "still",
                "start_sec": 0,
                "end_sec": 10,
                "beat": "opening",
                "characters_present": ["protagonist"],
                "identity_lock": {"protagonist": "strict"},
                "visual_prompt": {"environment": "river at dawn"},
                "asset_path": "images/scenes/scene_0001.png",
                "camera_motion": {"type": "slow_push_in", "intensity": 0.18},
                "transition_out": "crossfade",
            }
        ],
        "motion_shots": [
            {
                "id": "motion_0001",
                "scene_id": "scene_0001",
                "provider": "fake",
                "duration_sec": 6,
                "prompt": "wide moonlit action",
                "source_image_path": "images/scenes/scene_0001.png",
                "asset_path": "video/motion/motion_0001.mp4",
                "fallback_asset_path": "images/fallback_stills/motion_0001_fallback.png",
                "audio_policy": "strip",
            }
        ],
        "validation": {
            "require_character_review": True,
            "required_assets": {
                "character_refs": 2,
                "still_scenes_min": 1,
                "motion_shots": 1,
                "narration_segments_min": 1,
            },
        },
    }


def test_valid_blueprint_loads():
    blueprint = Blueprint.model_validate(valid_blueprint_dict())

    assert blueprint.episode.id == "river-debt"
    assert blueprint.scenes[0].characters_present == ["protagonist"]


def test_blueprint_rejects_scene_with_unknown_character():
    data = valid_blueprint_dict()
    data["scenes"][0]["characters_present"] = ["missing"]

    with pytest.raises(ValidationError, match="unknown character"):
        Blueprint.model_validate(data)


def test_blueprint_rejects_narration_with_unknown_scene():
    data = valid_blueprint_dict()
    data["narration"]["segments"][0]["scene_id"] = "missing"

    with pytest.raises(ValidationError, match="unknown scene"):
        Blueprint.model_validate(data)


def test_blueprint_rejects_motion_with_unknown_scene():
    data = valid_blueprint_dict()
    data["motion_shots"][0]["scene_id"] = "missing"

    with pytest.raises(ValidationError, match="unknown scene"):
        Blueprint.model_validate(data)


def test_blueprint_rejects_invalid_scene_timing():
    data = valid_blueprint_dict()
    data["scenes"][0]["end_sec"] = data["scenes"][0]["start_sec"]

    with pytest.raises(ValidationError, match="end_sec"):
        Blueprint.model_validate(data)


@pytest.mark.parametrize("duration_sec", [59, 91])
def test_blueprint_rejects_invalid_vertical_slice_duration(duration_sec: int):
    data = valid_blueprint_dict()
    data["episode"]["duration_sec"] = duration_sec

    with pytest.raises(ValidationError, match="duration"):
        Blueprint.model_validate(data)


def test_blueprint_rejects_parent_path_escape():
    data = valid_blueprint_dict()
    data["motion_shots"][0]["asset_path"] = "../outside.mp4"

    with pytest.raises(ValidationError, match="escape"):
        Blueprint.model_validate(data)


def test_load_blueprint_reads_json_file(tmp_path: Path):
    path = tmp_path / "blueprint.json"
    path.write_text(json.dumps(valid_blueprint_dict()), encoding="utf-8")

    blueprint = load_blueprint(path)

    assert blueprint.episode.duration_sec == 72


def test_validate_blueprint_file_returns_blueprint(tmp_path: Path):
    path = tmp_path / "blueprint.json"
    path.write_text(json.dumps(valid_blueprint_dict()), encoding="utf-8")

    blueprint = validate_blueprint_file(path)

    assert blueprint.motion_shots[0].id == "motion_0001"
