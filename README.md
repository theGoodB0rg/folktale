# Kuba-Engine

Kuba-Engine is a local-first, CLI-driven vertical slice for a headless African folktale video pipeline. The current implementation proves the production shape with deterministic fake providers and includes smoke-testable real provider adapters for Gemini, Kokoro, ComfyUI, Veo, and SiliconFlow.

This is not the full 15-minute production system yet. Production prompt quality, ComfyUI workflow tuning, voice tuning, and full-length pacing are still next milestones.

## Python Setup

```powershell
cd orchestrator
python -m pip install -e ".[dev]"
python -m pytest -v
```

For real local providers, install the optional runtime extras:

```powershell
cd orchestrator
python -m pip install -e ".[dev,real]"
```

## Fake Vertical Slice

The fake providers are deterministic test scaffolding. They let the full pipeline run without cloud credentials or local ML services.

```powershell
cd orchestrator
kuba doctor --check python
kuba episode create --output-root ../episodes --title "The River's Debt"
kuba script generate ../episodes/the-rivers-debt --fake
kuba refs generate ../episodes/the-rivers-debt --fake
kuba refs approve ../episodes/the-rivers-debt
kuba assets generate ../episodes/the-rivers-debt --fake
kuba assets validate ../episodes/the-rivers-debt
kuba resume ../episodes/the-rivers-debt --fake
```

The character reference checkpoint is intentional. `refs generate` writes character images and leaves the episode waiting for review. `refs approve` marks that checkpoint complete after the references validate as images.

## Environment

Real provider credentials and paths belong in `.env`, using `.env.example` as the template:

```text
GEMINI_API_KEY=
COMFYUI_BASE_URL=http://127.0.0.1:8188
KOKORO_MODEL_PATH=
KOKORO_VOICES_PATH=
KOKORO_VOICE=af_heart
KOKORO_SPEED=0.92
KUBA_SCRIPT_PROVIDER=fixture
KUBA_BLUEPRINT_FIXTURE=./config/blueprints/vertical_slice_fixture.json
SILICONFLOW_API_KEY=
KUBA_VIDEO_PROVIDER=siliconflow
FFMPEG_PATH=
REMOTION_CONCURRENCY=2
KUBA_DEFAULT_OUTPUT_ROOT=./episodes
```

## Real Provider Smoke Path

Real provider adapters are available behind explicit provider flags. Run doctor checks before generating assets:

```powershell
cd orchestrator
kuba doctor --check python
kuba doctor --check comfy
kuba doctor --check kokoro
kuba doctor --check gemini
kuba doctor --check siliconflow
```

Script generation can use Gemini:

```powershell
kuba script generate ../episodes/the-rivers-debt --provider gemini
```

During production media-pipeline testing, Gemini can be bypassed with a prevalidated blueprint fixture:

```powershell
kuba script generate ../episodes/the-rivers-debt --provider fixture --mode production `
  --blueprint-fixture ../config/blueprints/vertical_slice_fixture.json
```

The real ComfyUI image path requires a workflow saved in API format plus a YAML map identifying the node inputs to patch:

```powershell
kuba refs generate ../episodes/the-rivers-debt --provider comfy `
  --workflow ../config/comfy/workflows/sdxl_ip_adapter_api.json `
  --workflow-map ../config/comfy/workflows/sdxl_ip_adapter_api.map.yaml
```

Asset generation can mix local and cloud providers:

```powershell
kuba assets generate ../episodes/the-rivers-debt `
  --audio-provider kokoro `
  --image-provider comfy `
  --video-provider siliconflow `
  --workflow ../config/comfy/workflows/sdxl_ip_adapter_api.json `
  --workflow-map ../config/comfy/workflows/sdxl_ip_adapter_api.map.yaml
```

Use `--video-provider veo` for Gemini/Veo. Cloud video failures still use the configured image provider to create the fallback still.

Opt-in local integration checks are skipped by default. Enable them when your env vars and services are ready:

```powershell
$env:KUBA_RUN_REAL_INTEGRATION="1"
python -m pytest tests/test_local_integration.py -v
```

Production mode disables fake providers and treats video fallback stills as failed video generation:

```powershell
kuba doctor --check production
kuba script generate ../episodes/the-rivers-debt --provider gemini --mode production
kuba refs generate ../episodes/the-rivers-debt --provider comfy --mode production `
  --workflow ../config/comfy/workflows/sdxl_ip_adapter_api.json `
  --workflow-map ../config/comfy/workflows/sdxl_ip_adapter_api.map.yaml
kuba refs approve ../episodes/the-rivers-debt
kuba assets generate ../episodes/the-rivers-debt --mode production `
  --audio-provider kokoro `
  --image-provider comfy `
  --video-provider siliconflow `
  --workflow ../config/comfy/workflows/sdxl_ip_adapter_api.json `
  --workflow-map ../config/comfy/workflows/sdxl_ip_adapter_api.map.yaml
kuba assets validate ../episodes/the-rivers-debt --mode production
kuba render ../episodes/the-rivers-debt --quality preview --mode production
```

Remaining external production prerequisites:

- ComfyUI must be running at `COMFYUI_BASE_URL`.
- `KUBA_COMFY_WORKFLOW` must point to an exported ComfyUI API workflow JSON.
- `KUBA_COMFY_WORKFLOW_MAP` must point to the matching workflow map YAML.
- `SILICONFLOW_API_KEY` must be set for `KUBA_VIDEO_PROVIDER=siliconflow`, or use `KUBA_VIDEO_PROVIDER=veo` with `GEMINI_API_KEY`.

## Remotion

The Remotion package is a renderer shell. It does not call generation APIs.

```powershell
cd remotion
npm ci
npm run typecheck
npm run render:placeholder
npm run render:preview
```

`render:preview` uses `props.example.json` and static example assets under `remotion/public/example-episode`. `kuba render EPISODE --quality preview --mode production` writes episode-specific Remotion props and renders from validated generated assets.

## Current Scope

Implemented:

- Blueprint schema and path validation
- Episode state and manifests
- Media probes for images, audio, and video
- Deterministic fake script, audio, image, and video providers
- Real provider adapters for Gemini, Kokoro, ComfyUI, Veo, and SiliconFlow
- Strict production mode that disables fake providers and rejects video fallback stills
- Production doctor check for Gemini, Kokoro, ComfyUI, workflow map, ffmpeg/ffprobe, video provider credentials, and Remotion
- Character reference review checkpoint
- Asset validation and resume behavior
- CLI commands for the fake vertical slice
- Remotion composition shell

Not implemented yet:

- Production ComfyUI workflow templates
- Kokoro voice/cadence tuning
- Full 15-minute episode production
- Batch production dashboard
