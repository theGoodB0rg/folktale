# Kuba-Engine

Kuba-Engine is a local-first, CLI-driven vertical slice for a headless African folktale video pipeline. The current implementation proves the production shape with deterministic fake providers: script blueprint generation, character reference review, fake audio/image/video assets, fallback still handling, validation, resume behavior, and a Remotion renderer shell.

This is not the full 15-minute production system yet. Real Gemini, Kokoro, ComfyUI, Veo, and SiliconFlow integrations are the next provider milestones.

## Python Setup

```powershell
cd orchestrator
python -m pip install -e ".[dev]"
python -m pytest -v
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
SILICONFLOW_API_KEY=
FFMPEG_PATH=
REMOTION_CONCURRENCY=2
KUBA_DEFAULT_OUTPUT_ROOT=./episodes
```

## Remotion

The Remotion package is a renderer shell. It does not call generation APIs.

```powershell
cd remotion
npm ci
npm run typecheck
npm run render:placeholder
npm run render:preview
```

`render:preview` uses `props.example.json` and static example assets under `remotion/public/example-episode`. Generated episode rendering will be wired to real episode props in a later milestone.

## Current Scope

Implemented:

- Blueprint schema and path validation
- Episode state and manifests
- Media probes for images, audio, and video
- Deterministic fake script, audio, image, and video providers
- Character reference review checkpoint
- Asset validation and resume behavior
- CLI commands for the fake vertical slice
- Remotion composition shell

Not implemented yet:

- Real Gemini script generation
- Real Kokoro TTS
- Real ComfyUI workflow execution
- Real Veo/SiliconFlow motion generation
- Full 15-minute episode production
- Batch production dashboard
