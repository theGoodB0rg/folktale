# Kuba-Engine Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the tested v0.1 Kuba-Engine vertical slice CLI: schema/state contracts, episode creation, character review checkpoint, asset manifests, provider adapters with deterministic test providers, validation, resume behavior, and a Remotion renderer shell.

**Architecture:** Python owns orchestration, validation, provider boundaries, state, manifests, and CLI commands. Remotion remains a deterministic renderer that reads local blueprint/manifests; v0.1 includes the renderer package and timeline utilities, while Python tests cover the production state machine and integration flow with fake providers.

**Tech Stack:** Python 3.11+, Typer, Pydantic, PyYAML, pytest, Pillow, ffmpeg/ffprobe integration by subprocess, Node/TypeScript/Remotion for render package skeleton.

---

## File Map

Create these Python project files:

```text
orchestrator/pyproject.toml
orchestrator/src/kuba/__init__.py
orchestrator/src/kuba/cli.py
orchestrator/src/kuba/config.py
orchestrator/src/kuba/paths.py
orchestrator/src/kuba/blueprint/schema.py
orchestrator/src/kuba/blueprint/loader.py
orchestrator/src/kuba/blueprint/validator.py
orchestrator/src/kuba/state/episode_state.py
orchestrator/src/kuba/state/idempotency.py
orchestrator/src/kuba/media/audio_probe.py
orchestrator/src/kuba/media/image_probe.py
orchestrator/src/kuba/media/video_probe.py
orchestrator/src/kuba/providers/base.py
orchestrator/src/kuba/providers/fake.py
orchestrator/src/kuba/phases/episode_create.py
orchestrator/src/kuba/phases/script_generate.py
orchestrator/src/kuba/phases/character_refs.py
orchestrator/src/kuba/phases/audio_generate.py
orchestrator/src/kuba/phases/image_generate.py
orchestrator/src/kuba/phases/video_generate.py
orchestrator/src/kuba/phases/validate_assets.py
orchestrator/src/kuba/phases/render.py
orchestrator/src/kuba/phases/resume.py
orchestrator/src/kuba/doctor.py
```

Create these tests:

```text
orchestrator/tests/conftest.py
orchestrator/tests/test_blueprint_schema.py
orchestrator/tests/test_paths.py
orchestrator/tests/test_state_and_manifest.py
orchestrator/tests/test_media_probes.py
orchestrator/tests/test_character_refs_phase.py
orchestrator/tests/test_resume.py
orchestrator/tests/test_vertical_slice_integration.py
orchestrator/tests/test_cli.py
```

Create config/docs/package files:

```text
config/default.yaml
config/voices/narrator.yaml
config/comfy/workflows/sdxl_ip_adapter_api.json
config/comfy/workflows/sdxl_ip_adapter_api.map.yaml
.env.example
README.md
```

Create Remotion shell:

```text
remotion/package.json
remotion/tsconfig.json
remotion/remotion.config.ts
remotion/src/Root.tsx
remotion/src/compositions/FolktaleEpisode.tsx
remotion/src/components/SceneStill.tsx
remotion/src/components/MotionClip.tsx
remotion/src/components/CaptionLayer.tsx
remotion/src/lib/blueprint.ts
remotion/src/lib/timeline.ts
```

## Task 1: Python Package And Config Skeleton

**Files:**
- Create: `orchestrator/pyproject.toml`
- Create: `orchestrator/src/kuba/__init__.py`
- Create: `orchestrator/src/kuba/config.py`
- Create: `config/default.yaml`
- Create: `config/voices/narrator.yaml`
- Create: `.env.example`
- Test: `orchestrator/tests/test_cli.py`

- [ ] **Step 1: Write failing package import/config test**

```python
from pathlib import Path

from kuba.config import load_config


def test_load_config_reads_default_yaml(repo_root: Path):
    config = load_config(repo_root / "config" / "default.yaml")

    assert config.render.preview.width == 1280
    assert config.render.preview.height == 720
    assert config.render.final.width == 1920
    assert config.render.final.height == 1080
    assert config.comfy.base_url == "http://127.0.0.1:8188"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd orchestrator; python -m pytest tests/test_cli.py::test_load_config_reads_default_yaml -v`

Expected: FAIL because `kuba.config` does not exist.

- [ ] **Step 3: Implement config package**

Create `orchestrator/pyproject.toml` with package metadata, pytest config, and dependencies:

```toml
[project]
name = "kuba-engine"
version = "0.1.0"
description = "Headless folktale video generation pipeline"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.7",
  "PyYAML>=6.0",
  "typer>=0.12",
  "rich>=13.7",
  "Pillow>=10.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2"
]

[project.scripts]
kuba = "kuba.cli:app"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

Create `orchestrator/src/kuba/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `orchestrator/src/kuba/config.py` with Pydantic models and YAML loading:

```python
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class RenderSize(BaseModel):
    width: int
    height: int


class RenderConfig(BaseModel):
    fps: int
    preview: RenderSize
    final: RenderSize


class ComfyConfig(BaseModel):
    base_url: str
    workflow_path: str
    workflow_map_path: str


class Config(BaseModel):
    render: RenderConfig
    comfy: ComfyConfig


def load_config(path: Path) -> Config:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Config.model_validate(data)
```

Create `config/default.yaml`:

```yaml
render:
  fps: 30
  preview:
    width: 1280
    height: 720
  final:
    width: 1920
    height: 1080
comfy:
  base_url: "http://127.0.0.1:8188"
  workflow_path: "config/comfy/workflows/sdxl_ip_adapter_api.json"
  workflow_map_path: "config/comfy/workflows/sdxl_ip_adapter_api.map.yaml"
```

Create `config/voices/narrator.yaml`:

```yaml
voice_id: narrator
engine: kokoro
base_voice: selected_supported_voice
speed: 0.92
sample_rate: 24000
style_vector_path: null
pronunciation_overrides: {}
```

Create `.env.example`:

```text
GEMINI_API_KEY=
COMFYUI_BASE_URL=http://127.0.0.1:8188
KOKORO_MODEL_PATH=
KOKORO_VOICES_PATH=
SILICONFLOW_API_KEY=
FFMPEG_PATH=
REMOTION_CONCURRENCY=2
KUBA_DEFAULT_OUTPUT_ROOT=./episodes
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd orchestrator; python -m pytest tests/test_cli.py::test_load_config_reads_default_yaml -v`

Expected: PASS.

## Task 2: Blueprint Schema And Path Safety

**Files:**
- Create: `orchestrator/src/kuba/paths.py`
- Create: `orchestrator/src/kuba/blueprint/schema.py`
- Create: `orchestrator/src/kuba/blueprint/loader.py`
- Create: `orchestrator/src/kuba/blueprint/validator.py`
- Test: `orchestrator/tests/test_blueprint_schema.py`
- Test: `orchestrator/tests/test_paths.py`

- [ ] **Step 1: Write failing tests for blueprint validation and path safety**

```python
import pytest
from pydantic import ValidationError

from kuba.blueprint.schema import Blueprint
from kuba.paths import resolve_episode_path


def valid_blueprint_dict():
    return {
        "schema_version": "0.1",
        "episode": {"id": "river-debt", "title": "River Debt", "duration_sec": 72, "format": "youtube_landscape"},
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
            "required_assets": {"character_refs": 2, "still_scenes_min": 1, "motion_shots": 1, "narration_segments_min": 1},
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


def test_resolve_episode_path_rejects_absolute_and_parent_escape(tmp_path):
    episode = tmp_path / "episodes" / "river-debt"
    episode.mkdir(parents=True)

    with pytest.raises(ValueError, match="relative"):
        resolve_episode_path(episode, "C:/outside/file.png")

    with pytest.raises(ValueError, match="escape"):
        resolve_episode_path(episode, "../outside/file.png")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd orchestrator; python -m pytest tests/test_blueprint_schema.py tests/test_paths.py -v`

Expected: FAIL because blueprint and path modules do not exist.

- [ ] **Step 3: Implement blueprint models and path resolution**

Implement Pydantic models with validators for required scene character IDs, narration scene IDs, motion scene IDs, relative paths, scene timing, and duration bounds. Implement `resolve_episode_path(episode_root, relative_path)` to reject absolute paths and parent escapes.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd orchestrator; python -m pytest tests/test_blueprint_schema.py tests/test_paths.py -v`

Expected: PASS.

## Task 3: Episode State, Manifest, And Idempotency

**Files:**
- Create: `orchestrator/src/kuba/state/episode_state.py`
- Create: `orchestrator/src/kuba/state/idempotency.py`
- Test: `orchestrator/tests/test_state_and_manifest.py`

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path

from kuba.state.episode_state import EpisodeState, Manifest, ManifestEntry, PhaseStatus
from kuba.state.idempotency import should_skip_asset


def test_state_round_trips_phase_and_operation_id(tmp_path: Path):
    path = tmp_path / "state.json"
    state = EpisodeState.new()
    state.set_phase("video_generate", PhaseStatus.RUNNING)
    state.operation_ids["motion_0001"] = "operations/123"
    state.save(path)

    loaded = EpisodeState.load(path)

    assert loaded.phases["video_generate"] == PhaseStatus.RUNNING
    assert loaded.operation_ids["motion_0001"] == "operations/123"


def test_manifest_round_trips_completed_entry(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest = Manifest(entries=[
        ManifestEntry(asset_id="seg_0001", blueprint_ref="seg_0001", relative_path="audio/narration/seg_0001.wav", status="completed", provider="fake")
    ])
    manifest.save(manifest_path)

    loaded = Manifest.load(manifest_path)

    assert loaded.by_asset_id("seg_0001").relative_path == "audio/narration/seg_0001.wav"


def test_should_skip_asset_requires_manifest_and_probe_success(tmp_path: Path):
    existing = tmp_path / "asset.wav"
    existing.write_text("fake", encoding="utf-8")
    entry = ManifestEntry(asset_id="seg_0001", blueprint_ref="seg_0001", relative_path="asset.wav", status="completed", provider="fake")

    assert should_skip_asset(tmp_path, entry, lambda path: path.exists()) is True
    assert should_skip_asset(tmp_path, entry, lambda path: False) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd orchestrator; python -m pytest tests/test_state_and_manifest.py -v`

Expected: FAIL because state modules do not exist.

- [ ] **Step 3: Implement state, manifest, and skip checks**

Implement JSON persistence with enum statuses: `pending`, `running`, `waiting_for_review`, `completed`, `failed`, `skipped`, `fallback_used`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd orchestrator; python -m pytest tests/test_state_and_manifest.py -v`

Expected: PASS.

## Task 4: Media Probes

**Files:**
- Create: `orchestrator/src/kuba/media/audio_probe.py`
- Create: `orchestrator/src/kuba/media/image_probe.py`
- Create: `orchestrator/src/kuba/media/video_probe.py`
- Test: `orchestrator/tests/test_media_probes.py`

- [ ] **Step 1: Write failing tests for image and missing-media behavior**

```python
from pathlib import Path

from PIL import Image

from kuba.media.image_probe import probe_image
from kuba.media.audio_probe import probe_audio
from kuba.media.video_probe import probe_video


def test_probe_image_returns_dimensions(tmp_path: Path):
    path = tmp_path / "scene.png"
    Image.new("RGB", (1280, 720), color=(10, 20, 30)).save(path)

    info = probe_image(path)

    assert info.exists is True
    assert info.width == 1280
    assert info.height == 720
    assert info.valid is True


def test_probe_missing_audio_is_invalid(tmp_path: Path):
    info = probe_audio(tmp_path / "missing.wav")

    assert info.exists is False
    assert info.valid is False


def test_probe_missing_video_is_invalid(tmp_path: Path):
    info = probe_video(tmp_path / "missing.mp4")

    assert info.exists is False
    assert info.valid is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd orchestrator; python -m pytest tests/test_media_probes.py -v`

Expected: FAIL because media modules do not exist.

- [ ] **Step 3: Implement probes**

Implement image probing with Pillow. Implement audio/video probes that return invalid for missing files and use `ffprobe` when available for real files.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd orchestrator; python -m pytest tests/test_media_probes.py -v`

Expected: PASS.

## Task 5: Fake Providers And Episode Creation

**Files:**
- Create: `orchestrator/src/kuba/providers/base.py`
- Create: `orchestrator/src/kuba/providers/fake.py`
- Create: `orchestrator/src/kuba/phases/episode_create.py`
- Create: `orchestrator/src/kuba/phases/script_generate.py`
- Test: `orchestrator/tests/test_vertical_slice_integration.py`

- [ ] **Step 1: Write failing integration test for episode creation and fake script generation**

```python
from pathlib import Path

from kuba.blueprint.loader import load_blueprint
from kuba.phases.episode_create import create_episode
from kuba.phases.script_generate import generate_script
from kuba.providers.fake import FakeScriptProvider


def test_create_episode_and_generate_fake_blueprint(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")

    assert episode_root.name == "the-rivers-debt"
    assert (episode_root / "script" / "source.md").exists()

    generate_script(episode_root, FakeScriptProvider())

    blueprint = load_blueprint(episode_root / "blueprint.json")
    assert blueprint.episode.duration_sec == 78
    assert len(blueprint.characters) == 2
    assert len(blueprint.scenes) >= 5
    assert len(blueprint.motion_shots) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd orchestrator; python -m pytest tests/test_vertical_slice_integration.py::test_create_episode_and_generate_fake_blueprint -v`

Expected: FAIL because phases/providers do not exist.

- [ ] **Step 3: Implement fake provider and episode/script phases**

Implement deterministic `FakeScriptProvider` that returns the approved 60-90 second blueprint shape. Implement slugging, episode directory creation, `source.md`, `state.json`, and `blueprint.json` writing.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd orchestrator; python -m pytest tests/test_vertical_slice_integration.py::test_create_episode_and_generate_fake_blueprint -v`

Expected: PASS.

## Task 6: Character Reference Phase And Review Checkpoint

**Files:**
- Create: `orchestrator/src/kuba/phases/character_refs.py`
- Modify: `orchestrator/src/kuba/providers/fake.py`
- Test: `orchestrator/tests/test_character_refs_phase.py`

- [ ] **Step 1: Write failing tests for reference generation and approval**

```python
from pathlib import Path

from kuba.phases.character_refs import approve_refs, generate_refs
from kuba.phases.episode_create import create_episode
from kuba.phases.script_generate import generate_script
from kuba.providers.fake import FakeImageProvider, FakeScriptProvider
from kuba.state.episode_state import EpisodeState, PhaseStatus


def prepared_episode(tmp_path: Path) -> Path:
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    return episode_root


def test_generate_refs_writes_character_images_and_waits_for_review(tmp_path: Path):
    episode_root = prepared_episode(tmp_path)

    generated = generate_refs(episode_root, FakeImageProvider())

    assert len(generated) == 2
    assert (episode_root / "images" / "characters" / "protagonist_ref.png").exists()
    state = EpisodeState.load(episode_root / "state.json")
    assert state.phases["character_refs"] == PhaseStatus.WAITING_FOR_REVIEW


def test_approve_refs_marks_phase_completed(tmp_path: Path):
    episode_root = prepared_episode(tmp_path)
    generate_refs(episode_root, FakeImageProvider())

    approve_refs(episode_root)

    state = EpisodeState.load(episode_root / "state.json")
    assert state.phases["character_refs"] == PhaseStatus.COMPLETED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd orchestrator; python -m pytest tests/test_character_refs_phase.py -v`

Expected: FAIL because phase does not exist.

- [ ] **Step 3: Implement character refs phase**

Generate simple PNG files with `FakeImageProvider`, write `images/manifest.json`, and set state to `waiting_for_review`. Approval requires all character refs to exist and validate.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd orchestrator; python -m pytest tests/test_character_refs_phase.py -v`

Expected: PASS.

## Task 7: Audio, Still, Motion Fallback, Validation, And Resume

**Files:**
- Create: `orchestrator/src/kuba/phases/audio_generate.py`
- Create: `orchestrator/src/kuba/phases/image_generate.py`
- Create: `orchestrator/src/kuba/phases/video_generate.py`
- Create: `orchestrator/src/kuba/phases/validate_assets.py`
- Create: `orchestrator/src/kuba/phases/resume.py`
- Modify: `orchestrator/src/kuba/providers/fake.py`
- Test: `orchestrator/tests/test_resume.py`
- Test: `orchestrator/tests/test_vertical_slice_integration.py`

- [ ] **Step 1: Write failing integration test for full fake asset generation and fallback**

```python
from pathlib import Path

from kuba.phases.audio_generate import generate_audio
from kuba.phases.character_refs import approve_refs, generate_refs
from kuba.phases.episode_create import create_episode
from kuba.phases.image_generate import generate_images
from kuba.phases.script_generate import generate_script
from kuba.phases.validate_assets import validate_assets
from kuba.phases.video_generate import generate_video
from kuba.providers.fake import FakeAudioProvider, FakeImageProvider, FakeScriptProvider, FailingFakeVideoProvider


def test_full_fake_asset_generation_uses_fallback_when_video_fails(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    generate_refs(episode_root, FakeImageProvider())
    approve_refs(episode_root)

    generate_audio(episode_root, FakeAudioProvider())
    generate_images(episode_root, FakeImageProvider())
    generate_video(episode_root, FailingFakeVideoProvider(), FakeImageProvider())
    report = validate_assets(episode_root)

    assert report.ok is True
    assert (episode_root / "images" / "fallback_stills" / "motion_0001_fallback.png").exists()
```

- [ ] **Step 2: Write failing resume test**

```python
from pathlib import Path

from kuba.phases.audio_generate import generate_audio
from kuba.phases.episode_create import create_episode
from kuba.phases.resume import resume_episode
from kuba.phases.script_generate import generate_script
from kuba.providers.fake import FakeAudioProvider, FakeImageProvider, FakeScriptProvider


def test_resume_regenerates_missing_completed_audio(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    generate_audio(episode_root, FakeAudioProvider())
    missing = episode_root / "audio" / "narration" / "seg_0001.wav"
    missing.unlink()

    resume_episode(episode_root, audio_provider=FakeAudioProvider(), image_provider=FakeImageProvider())

    assert missing.exists()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd orchestrator; python -m pytest tests/test_vertical_slice_integration.py tests/test_resume.py -v`

Expected: FAIL because phases do not exist.

- [ ] **Step 4: Implement asset phases, validation report, and resume**

Implement fake WAV writing with Python `wave`, fake PNG writing with Pillow, failing video provider fallback still behavior, manifest writes, validation checks, and resume regeneration for missing completed assets.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd orchestrator; python -m pytest tests/test_vertical_slice_integration.py tests/test_resume.py -v`

Expected: PASS.

## Task 8: CLI And Doctor Command

**Files:**
- Create: `orchestrator/src/kuba/cli.py`
- Create: `orchestrator/src/kuba/doctor.py`
- Modify: `orchestrator/tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

```python
from typer.testing import CliRunner

from kuba.cli import app


def test_cli_doctor_runs_in_check_only_mode():
    runner = CliRunner()

    result = runner.invoke(app, ["doctor", "--check", "python"])

    assert result.exit_code == 0
    assert "python" in result.stdout.lower()


def test_cli_create_episode(tmp_path):
    runner = CliRunner()

    result = runner.invoke(app, ["episode", "create", "--output-root", str(tmp_path), "--title", "The River's Debt"])

    assert result.exit_code == 0
    assert (tmp_path / "the-rivers-debt" / "script" / "source.md").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd orchestrator; python -m pytest tests/test_cli.py -v`

Expected: FAIL because CLI is incomplete.

- [ ] **Step 3: Implement CLI**

Implement Typer command groups: `doctor`, `episode create`, `script generate --fake`, `refs generate --fake`, `refs approve`, `assets generate --fake`, `assets validate`, `resume`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd orchestrator; python -m pytest tests/test_cli.py -v`

Expected: PASS.

## Task 9: Remotion Renderer Shell And Timeline Tests

**Files:**
- Create: `remotion/package.json`
- Create: `remotion/tsconfig.json`
- Create: `remotion/remotion.config.ts`
- Create: `remotion/src/Root.tsx`
- Create: `remotion/src/compositions/FolktaleEpisode.tsx`
- Create: `remotion/src/components/SceneStill.tsx`
- Create: `remotion/src/components/MotionClip.tsx`
- Create: `remotion/src/components/CaptionLayer.tsx`
- Create: `remotion/src/lib/blueprint.ts`
- Create: `remotion/src/lib/timeline.ts`

- [ ] **Step 1: Create Remotion package shell**

Create a minimal Remotion package with scripts:

```json
{
  "name": "kuba-remotion",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "typecheck": "tsc --noEmit",
    "render:preview": "remotion render src/Root.tsx FolktaleEpisode ../episodes/the-rivers-debt/render/preview.mp4"
  },
  "dependencies": {
    "@remotion/cli": "^4.0.0",
    "@remotion/media-utils": "^4.0.0",
    "remotion": "^4.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0"
  }
}
```

- [ ] **Step 2: Implement timeline helper and components**

Implement `secondsToFrames(seconds, fps)` and basic components that render stills, motion clips, and captions from blueprint data.

- [ ] **Step 3: Run typecheck if dependencies are installed**

Run: `cd remotion; npm install; npm run typecheck`

Expected: PASS. If network or install fails, record the exact failure and keep Python test verification separate.

## Task 10: README, Full Verification, Commit

**Files:**
- Modify: `README.md`
- Modify: `.gitignore`

- [ ] **Step 1: Document setup and fake vertical slice**

README must include:

```text
Python setup
pytest command
kuba CLI example with fake providers
required real provider environment variables
character review checkpoint
Remotion render package note
```

- [ ] **Step 2: Run full Python verification**

Run: `cd orchestrator; python -m pytest -v`

Expected: all tests PASS.

- [ ] **Step 3: Run git status**

Run: `git status --short`

Expected: only intended files changed.

- [ ] **Step 4: Commit**

Run:

```bash
git add .
git commit -m "feat: implement kuba vertical slice foundation"
```

Expected: commit succeeds.

## Self-Review

Spec coverage:

```text
Python orchestrator: Tasks 1-8
Blueprint schema: Task 2
State/manifests/resume: Tasks 3 and 7
Character review checkpoint: Task 6
Fake provider boundaries for script/audio/image/video: Tasks 5-7
Fallback still behavior: Task 7
Doctor command: Task 8
Remotion shell: Task 9
Unit/integration tests: Tasks 1-8 and 10
Docs: Task 10
```

Known implementation boundary:

```text
Real Gemini, Kokoro, ComfyUI, Veo, and SiliconFlow network/provider implementations are represented by interfaces and deterministic fake providers in this first code pass. This keeps unit and integration tests reliable while preserving the architecture needed to plug in real providers next.
```

Placeholder scan: no task contains unresolved TBD/TODO instructions.

Type consistency: file names, phase names, state names, and command names are consistent across tasks.
