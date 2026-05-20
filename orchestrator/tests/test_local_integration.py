import os
from pathlib import Path

import pytest
from PIL import Image

from kuba.doctor import check_comfy, run_doctor_check
from kuba.blueprint.schema import Blueprint
from kuba.media.audio_probe import probe_audio
from kuba.media.image_probe import probe_image
from kuba.media.video_probe import probe_video
from kuba.providers.comfyui import ComfyUIImageProvider
from kuba.providers.gemini import GeminiScriptProvider
from kuba.providers.kokoro import KokoroAudioProvider
from kuba.providers.siliconflow import SiliconFlowVideoProvider
from kuba.providers.veo import GeminiVeoVideoProvider


def _real_integration_enabled() -> bool:
    return os.environ.get("KUBA_RUN_REAL_INTEGRATION") == "1"


def test_local_comfy_doctor_when_enabled():
    if not _real_integration_enabled():
        pytest.skip("set KUBA_RUN_REAL_INTEGRATION=1 to run real provider checks")

    result = check_comfy()

    assert result.ok, result.message


def test_local_kokoro_paths_when_enabled():
    if not _real_integration_enabled():
        pytest.skip("set KUBA_RUN_REAL_INTEGRATION=1 to run real provider checks")

    result = run_doctor_check("kokoro")

    assert result.ok, result.message


def test_local_gemini_key_when_enabled():
    if not _real_integration_enabled():
        pytest.skip("set KUBA_RUN_REAL_INTEGRATION=1 to run real provider checks")

    result = run_doctor_check("gemini")

    assert result.ok, result.message


def test_production_doctor_when_enabled():
    if not _real_integration_enabled():
        pytest.skip("set KUBA_RUN_REAL_INTEGRATION=1 to run real provider checks")

    result = run_doctor_check("production")

    assert result.ok, result.message


def test_real_gemini_generates_schema_valid_blueprint_when_enabled(tmp_path: Path):
    if not _real_integration_enabled():
        pytest.skip("set KUBA_RUN_REAL_INTEGRATION=1 to run real provider checks")

    payload = GeminiScriptProvider().generate_script(
        "# The River's Debt\nA short folktale about a river bargain.",
        "the-rivers-debt",
    )

    Blueprint.model_validate(payload)


def test_real_kokoro_generates_probeable_wav_when_enabled(tmp_path: Path):
    if not _real_integration_enabled():
        pytest.skip("set KUBA_RUN_REAL_INTEGRATION=1 to run real provider checks")

    output = KokoroAudioProvider().generate_audio(
        str(tmp_path),
        "audio/narration/smoke.wav",
        "The river remembered every promise.",
        2,
    )
    probe = probe_audio(Path(output))

    assert probe.valid, probe.error


def test_real_comfy_generates_probeable_image_when_enabled(tmp_path: Path):
    if not _real_integration_enabled():
        pytest.skip("set KUBA_RUN_REAL_INTEGRATION=1 to run real provider checks")

    workflow = Path(
        os.environ.get(
            "KUBA_COMFY_WORKFLOW",
            Path(__file__).resolve().parents[2]
            / "config"
            / "comfy"
            / "workflows"
            / "sdxl_ip_adapter_api.json",
        )
    )
    workflow_map = Path(
        os.environ.get(
            "KUBA_COMFY_WORKFLOW_MAP",
            Path(__file__).resolve().parents[2]
            / "config"
            / "comfy"
            / "workflows"
            / "sdxl_ip_adapter_api.map.yaml",
        )
    )
    provider = ComfyUIImageProvider(workflow_path=workflow, workflow_map_path=workflow_map)

    output = provider.generate_image(
        str(tmp_path),
        "images/scenes/comfy_smoke.png",
        "cinematic African riverside village at dawn, simple smoke test",
    )
    probe = probe_image(Path(output))

    assert probe.valid, probe.error


def test_real_video_provider_generates_probeable_mp4_when_enabled(tmp_path: Path):
    if not _real_integration_enabled():
        pytest.skip("set KUBA_RUN_REAL_INTEGRATION=1 to run real provider checks")

    source = tmp_path / "images" / "scenes" / "source.png"
    source.parent.mkdir(parents=True)
    Image.new("RGB", (1280, 720), color=(20, 50, 70)).save(source)
    provider_name = os.environ.get("KUBA_VIDEO_PROVIDER", "siliconflow").lower()
    if provider_name == "veo":
        provider = GeminiVeoVideoProvider()
    else:
        provider = SiliconFlowVideoProvider()

    output = provider.generate_video(
        str(tmp_path),
        "video/motion/smoke.mp4",
        "images/scenes/source.png",
        "A slow cinematic push across moonlit river reeds, no text, no captions.",
        5,
    )
    probe = probe_video(Path(output))

    assert probe.valid, probe.error
