import json
import base64
from pathlib import Path
import sys
import types
import wave

from PIL import Image

from kuba.providers.comfyui import ComfyUIClient, ComfyUIImageProvider, patch_workflow
from kuba.providers.gemini import GeminiScriptProvider
from kuba.providers.kokoro import KokoroAudioProvider
from kuba.providers.kokoro import _load_kokoro_engine
from kuba.providers.siliconflow import SiliconFlowClient, SiliconFlowVideoProvider
from kuba.providers.veo import GeminiVeoVideoProvider


def test_patch_workflow_updates_mapped_inputs():
    workflow = {
        "1": {"inputs": {"text": "old"}},
        "2": {"inputs": {"filename_prefix": "old"}},
    }
    mapping = {
        "positive_prompt": "1.inputs.text",
        "save_prefix": "2.inputs.filename_prefix",
    }

    patched = patch_workflow(
        workflow,
        mapping,
        positive_prompt="new prompt",
        negative_prompt="",
        seed=123,
        output_prefix="kuba/scene_0001",
        reference_image_path=None,
    )

    assert patched["1"]["inputs"]["text"] == "new prompt"
    assert patched["2"]["inputs"]["filename_prefix"] == "kuba/scene_0001"
    assert workflow["1"]["inputs"]["text"] == "old"


def test_patch_workflow_bypasses_ip_adapter_when_reference_image_is_missing():
    workflow = {
        "1": {"inputs": {"ckpt_name": "model.safetensors"}, "class_type": "CheckpointLoaderSimple"},
        "2": {"inputs": {"text": "", "clip": ["1", 1]}, "class_type": "CLIPTextEncode"},
        "3": {"inputs": {"text": "", "clip": ["1", 1]}, "class_type": "CLIPTextEncode"},
        "4": {"inputs": {"width": 512, "height": 512, "batch_size": 1}, "class_type": "EmptyLatentImage"},
        "5": {"inputs": {"image": ""}, "class_type": "LoadImage"},
        "6": {"inputs": {"model": ["1", 0], "preset": "PLUS (high strength)"}, "class_type": "IPAdapterUnifiedLoader"},
        "7": {"inputs": {"model": ["6", 0], "ipadapter": ["6", 1], "image": ["5", 0]}, "class_type": "IPAdapter"},
        "8": {"inputs": {"model": ["7", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}, "class_type": "KSampler"},
        "9": {"inputs": {"samples": ["8", 0], "vae": ["1", 2]}, "class_type": "VAEDecode"},
        "10": {"inputs": {"images": ["9", 0], "filename_prefix": ""}, "class_type": "SaveImage"},
    }
    mapping = {
        "positive_prompt": "2.inputs.text",
        "save_prefix": "10.inputs.filename_prefix",
        "reference_image": "5.inputs.image",
    }

    patched = patch_workflow(
        workflow,
        mapping,
        positive_prompt="Nia portrait",
        negative_prompt="",
        seed=0,
        output_prefix="protagonist_ref",
        reference_image_path=None,
    )

    assert "5" not in patched
    assert "6" not in patched
    assert "7" not in patched
    assert patched["8"]["inputs"]["model"] == ["1", 0]


def test_comfy_provider_submits_polls_and_downloads_image(tmp_path: Path):
    workflow_path = tmp_path / "workflow.json"
    map_path = tmp_path / "workflow.map.yaml"
    workflow_path.write_text(
        json.dumps(
            {
                "1": {"inputs": {"text": ""}},
                "2": {"inputs": {"filename_prefix": ""}},
            }
        ),
        encoding="utf-8",
    )
    map_path.write_text(
        "positive_prompt: 1.inputs.text\nsave_prefix: 2.inputs.filename_prefix\n",
        encoding="utf-8",
    )

    image = Image.new("RGB", (8, 8), color=(1, 2, 3))
    image_path = tmp_path / "comfy-output.png"
    image.save(image_path)
    image_bytes = image_path.read_bytes()

    class Client:
        def post_prompt(self, prompt):
            assert prompt["1"]["inputs"]["text"] == "river"
            return "prompt-1"

        def wait_for_output_image(self, prompt_id):
            assert prompt_id == "prompt-1"
            return {"filename": "out.png", "subfolder": "", "type": "output"}

        def download_image(self, image_ref):
            assert image_ref["filename"] == "out.png"
            return image_bytes

    provider = ComfyUIImageProvider(
        workflow_path=workflow_path,
        workflow_map_path=map_path,
        client=Client(),
    )

    output = provider.generate_image(str(tmp_path), "images/scenes/scene.png", "river")

    assert Path(output).exists()
    assert Image.open(output).size == (8, 8)


def test_comfy_client_reads_base_url_from_environment(monkeypatch):
    monkeypatch.setenv("COMFYUI_BASE_URL", "https://example.test/")

    client = ComfyUIClient()

    assert client.base_url == "https://example.test"


def test_kokoro_provider_uses_injected_engine(tmp_path: Path):
    class Engine:
        def synthesize_to_wav(self, text, output_path, voice, speed):
            with wave.open(str(output_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(8000)
                wav_file.writeframes(b"\x00\x00" * 800)

    provider = KokoroAudioProvider(engine=Engine(), voice="af_test", speed=0.9)

    output = provider.generate_audio(str(tmp_path), "audio/narration/seg.wav", "hello", 1)

    assert Path(output).exists()


def test_kokoro_loader_supports_local_pytorch_model_layout(
    tmp_path: Path, monkeypatch
):
    model_path = tmp_path / "kokoro-v1_0.pth"
    voices_path = tmp_path / "voices"
    voice_path = voices_path / "af_heart.pt"
    model_path.write_text("model", encoding="utf-8")
    voices_path.mkdir()
    voice_path.write_text("voice", encoding="utf-8")

    created = {}

    class KPipeline:
        def __init__(self, lang_code, model):
            created["lang_code"] = lang_code
            created["model"] = model

    kokoro_module = types.SimpleNamespace(KPipeline=KPipeline)
    monkeypatch.setitem(sys.modules, "kokoro", kokoro_module)

    engine = _load_kokoro_engine(str(model_path), str(voices_path))

    assert engine.model_path == model_path
    assert engine.voices_path == voices_path
    assert created["model"] == str(model_path)


def test_gemini_script_provider_extracts_json_payload():
    class Client:
        def generate_json(self, prompt, schema):
            assert "source" in prompt.lower()
            return {
                "schema_version": "0.1",
                "episode": {
                    "id": "river",
                    "title": "River",
                    "duration_sec": 60,
                    "format": "youtube_landscape",
                },
                "render": {
                    "fps": 30,
                    "preview": {"width": 1280, "height": 720},
                    "final": {"width": 1920, "height": 1080},
                    "audio": {"mode": "narration_only", "normalize": True},
                },
                "style": {"visual_style": "x", "palette": "x", "negative_prompt": "x"},
                "characters": [
                    {
                        "id": "protagonist",
                        "role": "main",
                        "display_name": "A",
                        "consistency_scope": "episode",
                        "reference_image_path": "images/characters/a.png",
                        "identity_lock": {"priority": "strict"},
                        "identity_prompt": {"face": "x"},
                        "flexibility": {"pose": "flexible"},
                    },
                    {
                        "id": "elder",
                        "role": "elder",
                        "display_name": "B",
                        "consistency_scope": "episode",
                        "reference_image_path": "images/characters/b.png",
                        "identity_lock": {"priority": "strict"},
                        "identity_prompt": {"face": "x"},
                        "flexibility": {"pose": "flexible"},
                    },
                ],
                "narration": {
                    "voice_profile": "config/voices/narrator.yaml",
                    "segments": [
                        {
                            "id": "seg_0001",
                            "scene_id": "scene_0001",
                            "text": "hello",
                            "start_sec": 0,
                            "target_duration_sec": 60,
                            "audio_path": "audio/narration/seg_0001.wav",
                        }
                    ],
                },
                "scenes": [
                    {
                        "id": "scene_0001",
                        "type": "still",
                        "start_sec": 0,
                        "end_sec": 60,
                        "beat": "open",
                        "characters_present": ["protagonist"],
                        "identity_lock": {"protagonist": "strict"},
                        "visual_prompt": {"environment": "river"},
                        "asset_path": "images/scenes/scene_0001.png",
                        "camera_motion": {"type": "static", "intensity": 0},
                        "transition_out": "crossfade",
                    }
                ],
                "motion_shots": [
                    {
                        "id": "motion_0001",
                        "scene_id": "scene_0001",
                        "provider": "veo",
                        "duration_sec": 6,
                        "prompt": "mist",
                        "source_image_path": "images/scenes/scene_0001.png",
                        "asset_path": "video/motion/motion_0001.mp4",
                        "fallback_asset_path": "images/fallback_stills/motion_0001.png",
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

    provider = GeminiScriptProvider(client=Client())

    payload = provider.generate_script("source", "river")

    assert payload["episode"]["id"] == "river"


def test_veo_provider_polls_operation_and_writes_video(tmp_path: Path):
    class Client:
        def submit_video(self, prompt, source_image_path, duration_sec):
            return "op-1"

        def wait_for_video_bytes(self, operation_id):
            assert operation_id == "op-1"
            return b"video-bytes"

    provider = GeminiVeoVideoProvider(client=Client())

    output = provider.generate_video(
        str(tmp_path),
        "video/motion/motion.mp4",
        "images/scenes/scene.png",
        "mist",
        6,
    )

    assert Path(output).read_bytes() == b"video-bytes"


def test_siliconflow_provider_polls_request_and_writes_video(tmp_path: Path):
    class Client:
        def submit_video(self, prompt, source_image_path, duration_sec):
            assert prompt == "mist"
            assert source_image_path == str(tmp_path / "images/scenes/scene.png")
            return "request-1"

        def wait_for_video_bytes(self, request_id):
            assert request_id == "request-1"
            return b"silicon-video"

    provider = SiliconFlowVideoProvider(client=Client())
    source = tmp_path / "images/scenes/scene.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"png")

    output = provider.generate_video(
        str(tmp_path),
        "video/motion/motion.mp4",
        "images/scenes/scene.png",
        "mist",
        6,
    )

    assert Path(output).read_bytes() == b"silicon-video"


def test_siliconflow_client_submits_image_to_video_payload(tmp_path: Path, monkeypatch):
    source = tmp_path / "scene.png"
    Image.new("RGB", (1024, 768), "blue").save(source)
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"requestId":"request-1"}'

    def fake_urlopen(request, timeout):
        requests.append(request)
        return Response()

    monkeypatch.setattr("kuba.providers.siliconflow.urlopen", fake_urlopen)

    client = SiliconFlowClient(api_key="key")
    request_id = client.submit_video("mist", str(source), 6)

    payload = json.loads(requests[0].data.decode("utf-8"))
    assert request_id == "request-1"
    assert payload["model"] == "Wan-AI/Wan2.2-I2V-A14B"
    assert payload["prompt"] == "mist"
    assert payload["image_size"] == "720x1280"
    assert payload["image"].startswith("data:image/jpeg;base64,")
    decoded = base64.b64decode(payload["image"].split(",", 1)[1])
    assert decoded.startswith(b"\xff\xd8")
