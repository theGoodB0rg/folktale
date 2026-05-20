# Kuba-Engine Vertical Slice Design

Date: 2026-05-20

## Status

Approved discussion sections have been consolidated into this design spec. This document defines the first implementation target for `Kuba-Engine`: a 60-90 second vertical slice that exercises the full headless folktale video pipeline once.

## Source Context

The project brief in `docs/project_initial_brief.md` describes a local-first, CLI-driven pipeline for producing African folktale anthology videos. The long-term target is approximately 15-minute YouTube videos assembled from local narration, character-consistent still images, selective high-impact motion clips, and Remotion rendering.

This first design intentionally narrows the scope to a short proof of concept. The goal is to validate architecture, provider integrations, state persistence, character consistency, fallback behavior, and rendering before scaling to full-length episodes.

## First Milestone Scope

The first milestone is a 60-90 second 16:9 YouTube-style proof of concept.

Target output:

```text
Output:
  episodes/<episode-id>/render/preview.mp4

Duration:
  60-90 seconds

Format:
  1280x720 preview render
  1920x1080 final target
  30 fps
  MP4 / H.264
  Narration-led
  Generated clip audio stripped or ignored

Assets:
  5-8 Kokoro narration WAV segments
  2 recurring character references
  5-8 ComfyUI still scenes
  1 cloud-generated motion clip
  1 fallback still for the motion clip path

Pipeline systems represented:
  Gemini/script engine
  Kokoro TTS
  ComfyUI still generation
  Veo or SiliconFlow motion generation
  validation
  Remotion composition
```

The story is standalone. Character continuity is required inside the episode only, not across multiple YouTube videos.

## Story And Visual Requirements

The first vertical slice should use a compact folktale structure:

```text
Beat 1: Establish the village/world
Beat 2: Introduce protagonist
Beat 3: Introduce elder or antagonist
Beat 4: Warning, bargain, curse, or mystery
Beat 5: Journey or confrontation
Beat 6: High-impact motion shot
Beat 7: Consequence or reveal
Beat 8: Closing moral image
```

Cinematic variety is allowed and expected as the story beat demands. The system may vary environment, lighting, camera distance, lens feel, pose, emotional tone, weather, and background elements.

Recurring important characters must remain recognizable at a glance. Identity anchors include:

```text
Required:
  face structure
  age
  skin tone
  hairstyle
  body type or silhouette
  signature clothing or accessories
  dominant character colors

Flexible:
  expression
  pose
  camera angle
  lighting
  weathering or minor clothing distress
```

For the vertical slice, use two episode-local recurring characters:

```text
1. Protagonist
   Appears in most still scenes and possibly the motion clip.

2. Elder, antagonist, or other important recurring character
   Appears in 2-3 scenes.
```

## Required Character Reference Review

Character references are a mandatory review checkpoint in v0.1.

```text
1. Generate protagonist reference.
2. Generate elder/antagonist reference.
3. Stop for user review.
4. User approves or regenerates references.
5. Continue to scene, image, video, and render generation.
```

The checkpoint prevents a weak or incorrect character reference from contaminating every downstream scene image.

The CLI should expose this flow:

```text
kuba refs generate episodes/<episode-id>
kuba refs approve episodes/<episode-id>
kuba refs regenerate episodes/<episode-id> --character protagonist
```

## Recommended Repository Layout

```text
C:\Users\HP\Desktop\Personal Websites\folktales\
  docs\
    project_initial_brief.md
    superpowers\
      specs\
        2026-05-20-kuba-engine-vertical-slice-design.md

  config\
    default.yaml
    voices\
      narrator.yaml
    comfy\
      workflows\
        sdxl_ip_adapter_api.json
        sdxl_ip_adapter_api.map.yaml

  episodes\
    <episode-id>\
      blueprint.json
      state.json
      logs\
        run.log
        errors.jsonl

      script\
        source.md
        generated_script.json

      audio\
        narration\
          seg_0001.wav
          seg_0002.wav
        manifest.json

      images\
        characters\
          protagonist_ref.png
          elder_ref.png
        scenes\
          scene_0001.png
          scene_0002.png
        fallback_stills\
          motion_0001_fallback.png
        manifest.json

      video\
        motion\
          motion_0001.mp4
        manifest.json

      render\
        preview.mp4
        final.mp4
        render-report.json

  orchestrator\
    pyproject.toml
    src\
      kuba\
        cli.py
        config.py

        blueprint\
          schema.py
          loader.py
          validator.py

        phases\
          script_generate.py
          character_refs.py
          audio_generate.py
          image_generate.py
          video_generate.py
          validate_assets.py
          render.py

        providers\
          gemini.py
          kokoro.py
          comfyui.py
          veo.py
          siliconflow.py

        media\
          audio_probe.py
          image_probe.py
          video_probe.py

        state\
          episode_state.py
          idempotency.py

        logging.py

  remotion\
    package.json
    remotion.config.ts
    src\
      Root.tsx
      compositions\
        FolktaleEpisode.tsx
      components\
        SceneStill.tsx
        MotionClip.tsx
        CaptionLayer.tsx
      lib\
        blueprint.ts
        timeline.ts

  tools\
    validate_blueprint.py
    probe_comfy.py
    probe_kokoro.py
    probe_video_provider.py

  .env.example
  .gitignore
  README.md
```

## Architecture Boundary

Use a Python-first orchestrator and isolate Remotion as the renderer package.

```text
Python orchestrator:
  - creates blueprint
  - manages state
  - calls Gemini
  - calls Kokoro
  - calls ComfyUI
  - calls Veo or SiliconFlow
  - validates files
  - invokes Remotion

Remotion:
  - reads blueprint
  - reads generated assets
  - maps seconds to frames
  - applies pans, zooms, and transitions
  - exports MP4
```

Remotion should not call generation APIs or make production decisions. It should render from already validated local data.

## Language Recommendation

Use Python for the orchestrator and TypeScript/React for Remotion.

Python advantages:

```text
Pros:
  Better fit for Kokoro, ONNX, and local ML tooling.
  Easier media probing and validation.
  Strong fit for long-running CLI workflows.
  Cleaner file and state orchestration.
  Good retry, progress, and logging ecosystem.

Cons:
  Requires both Python and Node.
  Blueprint types must be shared carefully with Remotion.
  Packaging is slightly more complex.
```

Mitigation: use JSON Schema as the contract between Python and TypeScript.

```text
orchestrator owns:
  blueprint.schema.json

Python validates:
  blueprint.json against schema

TypeScript validates or imports:
  blueprint.json before render
```

## Command Flow

The initial CLI should support explicit phase commands:

```text
kuba doctor

kuba episode create --title "The River's Debt"

kuba script generate episodes/the-rivers-debt

kuba refs generate episodes/the-rivers-debt
# stops for user review

kuba refs approve episodes/the-rivers-debt

kuba assets generate episodes/the-rivers-debt

kuba assets validate episodes/the-rivers-debt

kuba render episodes/the-rivers-debt --quality preview
```

Later convenience commands may be added:

```text
kuba run episodes/the-rivers-debt --until review
kuba resume episodes/the-rivers-debt
```

## Phase Flow

```text
[doctor]
   |
   v
[script_generate]
   |
   v
[character_refs]
   |
   v
[manual review checkpoint]
   |
   v
[audio_generate] ----\
                      \
[image_generate] ------> [validate_assets] -> [render]
                      /
[video_generate] ----/
```

For v0.1, use low concurrency or mostly sequential generation. Higher concurrency can be added after the vertical slice proves reliable.

## Blueprint Schema Direction

`blueprint.json` is the intended episode plan. It should not become a runtime event log.

Recommended top-level shape:

```text
blueprint.json
  schema_version
  episode
  render
  style
  characters
  narration
  scenes
  motion_shots
  validation
```

Conceptual example:

```json
{
  "schema_version": "0.1",
  "episode": {
    "id": "the-rivers-debt",
    "title": "The River's Debt",
    "duration_sec": 78,
    "format": "youtube_landscape"
  },
  "render": {
    "fps": 30,
    "preview": {
      "width": 1280,
      "height": 720
    },
    "final": {
      "width": 1920,
      "height": 1080
    },
    "audio": {
      "mode": "narration_only",
      "normalize": true
    }
  },
  "style": {
    "visual_style": "cinematic African folktale anthology, painterly realism, dramatic natural light",
    "palette": "earth tones, deep greens, firelight amber, moonlit blue where story demands",
    "negative_prompt": "modern clothing, text, watermark, distorted hands, extra fingers, inconsistent face"
  },
  "characters": [
    {
      "id": "protagonist",
      "role": "main",
      "display_name": "Amina",
      "consistency_scope": "episode",
      "reference_image_path": "images/characters/protagonist_ref.png",
      "identity_lock": {
        "priority": "strict",
        "face": "required",
        "age": "required",
        "skin_tone": "required",
        "hairstyle": "required",
        "body_silhouette": "required",
        "signature_clothing": "required",
        "accessories": "preferred"
      },
      "identity_prompt": {
        "age": "young adult woman",
        "face": "oval face, calm alert eyes, defined cheekbones",
        "hairstyle": "short natural braids pulled back",
        "clothing": "indigo wrapper with red woven sash",
        "accessories": "small brass earrings"
      },
      "flexibility": {
        "expression": "flexible",
        "pose": "flexible",
        "lighting": "flexible",
        "weathering": "limited"
      }
    }
  ],
  "narration": {
    "voice_profile": "config/voices/narrator.yaml",
    "segments": [
      {
        "id": "seg_0001",
        "scene_id": "scene_0001",
        "text": "Before the harmattan winds crossed the valley, Amina heard the river call her name.",
        "start_sec": 0,
        "target_duration_sec": 9,
        "audio_path": "audio/narration/seg_0001.wav"
      }
    ]
  },
  "scenes": [
    {
      "id": "scene_0001",
      "type": "still",
      "start_sec": 0,
      "end_sec": 9,
      "beat": "establish the world and protagonist",
      "characters_present": ["protagonist"],
      "identity_lock": {
        "protagonist": "strict"
      },
      "visual_prompt": {
        "environment": "wide riverside village at dawn",
        "action": "Amina stands near the water, listening",
        "camera": "wide cinematic shot, gentle low angle",
        "lighting": "soft sunrise mist",
        "mood": "mysterious and reverent"
      },
      "asset_path": "images/scenes/scene_0001.png",
      "camera_motion": {
        "type": "slow_push_in",
        "intensity": 0.18
      },
      "transition_out": "crossfade"
    }
  ],
  "motion_shots": [
    {
      "id": "motion_0001",
      "scene_id": "scene_0006",
      "provider": "veo",
      "duration_sec": 6,
      "prompt": "wide cinematic shot of Amina running through moonlit reeds as river spirits rise like glowing mist",
      "source_image_path": "images/scenes/scene_0006.png",
      "asset_path": "video/motion/motion_0001.mp4",
      "fallback_asset_path": "images/fallback_stills/motion_0001_fallback.png",
      "audio_policy": "strip"
    }
  ],
  "validation": {
    "require_character_review": true,
    "required_assets": {
      "character_refs": 2,
      "still_scenes_min": 5,
      "motion_shots": 1,
      "narration_segments_min": 5
    }
  }
}
```

Use relative paths inside the blueprint. The orchestrator resolves them relative to `episodes/<episode-id>/`.

```text
Good:
  images/scenes/scene_0001.png

Rejected:
  C:\absolute\path\scene_0001.png
  ..\outside-episode\secret.txt
```

## Timing Policy

Each scene has planned `start_sec` and `end_sec`. Narration segments have `target_duration_sec`.

The validation phase compares actual WAV durations against the planned timing. For v0.1, validation should adjust render timing to actual narration duration when needed, then write the adjustment into a report.

```text
Preferred v0.1 behavior:
  detect drift
  adjust render timing
  report adjustment
  continue if drift is within configured tolerance
```

This is more forgiving than failing every run because TTS duration is approximate.

## State And Manifest Model

Use three separate layers:

```text
blueprint.json
  The intended episode plan.
  Scenes, narration text, prompts, timing, required assets.

state.json
  Runtime progress.
  Current phase, retry counts, provider operation IDs, failures.

manifest.json files
  Verified outputs.
  Actual file paths, durations, dimensions, hashes, status.
```

Example responsibility split:

```text
blueprint.json says:
  scene_0004 requires protagonist and elder from 24.0s to 36.0s

state.json says:
  scene_0004 image generation failed once, retry scheduled

images/manifest.json says:
  scene_0004.png exists, 1920x1080, valid PNG, generated at timestamp X
```

Each asset manifest entry should include:

```text
asset_id
blueprint_ref
relative_path
status
provider
created_at
updated_at
duration_sec if applicable
width and height if applicable
hash
error if failed
```

## Resume Behavior

Core rule:

```text
Never decide from filenames alone.
Decide from:
  blueprint.json + state.json + manifest.json + media validation
```

On `kuba resume episodes/<episode-id>`:

```text
1. Load blueprint.json.
2. Load state.json if present.
3. Load manifests if present.
4. Validate all completed asset records.
5. Mark missing or corrupt assets as pending.
6. Continue from the earliest incomplete required phase.
```

Examples:

```text
audio/narration/seg_0001.wav exists
manifest says duration: 8.7 sec
audio probe confirms readable WAV
blueprint expects seg_0001
=> skip

images/scenes/scene_0004.png exists
manifest says completed
image probe fails
=> mark scene_0004 pending and regenerate

video/motion/motion_0001.mp4 missing
state has operation_id from Veo
=> poll existing operation before submitting a new job
```

## Phase States

Recommended states:

```text
pending
running
waiting_for_review
completed
failed
skipped
fallback_used
```

Recommended phase transitions:

```text
script_generate: pending -> running -> completed
character_refs: pending -> running -> waiting_for_review -> completed
audio_generate: pending -> running -> completed
image_generate: pending -> running -> completed
video_generate: pending -> running -> completed | fallback_used
validate_assets: pending -> running -> completed | failed
render: pending -> running -> completed | failed
```

## Validation Layers

Use validation at three levels:

```text
1. Blueprint validation
   - required fields exist
   - scene timings are sane
   - referenced character IDs exist
   - paths are relative and cannot escape episode folder
   - motion shots point to valid scenes

2. Asset validation
   - WAV files exist and are readable
   - PNG files exist and match expected dimensions
   - MP4 files exist, are readable, and have expected duration
   - generated video audio is stripped or ignored

3. Render validation
   - Remotion can parse blueprint
   - timeline duration matches expected output
   - all render-selected assets exist
   - preview MP4 exists after render
```

## Retry And Failure Policy

Recommended v0.1 retry policy:

```text
Gemini/script:       2 retries
Kokoro/audio:        1 retry
ComfyUI/images:      2 retries
Veo/video polling:   bounded wait, then fallback still
Remotion/render:     no blind retry; fail with logs
```

For cloud video:

```text
Submit motion job
  |
  v
Persist operation_id immediately
  |
  v
Poll with backoff
  |
  +-- success -> download MP4 -> strip audio -> validate -> use motion clip
  |
  +-- timeout/failure/rate limit -> generate fallback still -> mark fallback_used
```

The final render should not fail permanently just because the cloud video provider failed. It should use:

```text
video/motion/motion_0001.mp4
```

or:

```text
images/fallback_stills/motion_0001_fallback.png
```

## Provider Recommendations

### Gemini Script And Blueprint Generation

Gemini should generate structured draft data. The orchestrator must validate, normalize, and write final `blueprint.json`.

Paths:

```text
episodes/<episode-id>/
  script/
    source.md
    generated_script.json
  blueprint.json
```

Risks:

```text
LLM output may violate timing or schema.
Prompts may be too vague or too long.
Narration duration estimates will be approximate.
```

Mitigations:

```text
Validate against schema.
Normalize IDs and paths.
Enforce 60-90 second duration.
Require exactly 5-8 scenes and 1 motion shot.
Keep character identity data separate from scene prompts.
```

### Kokoro TTS

Use Kokoro through Python, with voice settings defined in `config/voices/narrator.yaml`.

Paths:

```text
config/
  voices/
    narrator.yaml

episodes/<episode-id>/
  audio/
    narration/
      seg_0001.wav
      seg_0002.wav
    manifest.json
```

Voice config concept:

```text
voice_id: narrator
engine: kokoro
model_path: ${KOKORO_MODEL_PATH}
voices_path: ${KOKORO_VOICES_PATH}
base_voice: selected_supported_voice
speed: 0.92
sample_rate: 24000
style_vector_path: optional
pronunciation_overrides:
  Amina: "..."
  Ogun: "..."
```

Recommendation for v0.1: start with a known working Kokoro voice. Add custom style-vector experiments after the basic pipeline renders.

Risks:

```text
Custom African cadence may not be achievable by vector injection alone.
Pronunciation of names may require overrides.
Segment boundaries can sound unnatural.
```

Mitigations:

```text
Generate scene-sized narration segments, not tiny sentence fragments.
Add 150-300ms padding or crossfade room in Remotion if needed.
Support pronunciation overrides.
Treat custom voice tuning as a separate milestone.
```

### ComfyUI Still Images

Use ComfyUI headless API with fixed workflow templates and mapping files.

Paths:

```text
config/
  comfy/
    workflows/
      sdxl_ip_adapter_api.json
      sdxl_ip_adapter_api.map.yaml

episodes/<episode-id>/
  images/
    characters/
      protagonist_ref.png
      elder_ref.png
    scenes/
      scene_0001.png
      scene_0002.png
    fallback_stills/
      motion_0001_fallback.png
    manifest.json
```

Template model:

```text
sdxl_ip_adapter_api.json
  Full ComfyUI workflow in API format.

sdxl_ip_adapter_api.map.yaml
  positive_prompt_node: ...
  negative_prompt_node: ...
  seed_node: ...
  ip_adapter_image_node: ...
  save_prefix_node: ...
  width_node: ...
  height_node: ...
```

Generation prompt model:

```text
global visual style
+ character identity prompt(s)
+ scene visual prompt
+ negative prompt
+ reference image(s)
=> ComfyUI workflow payload
```

Risks:

```text
IP-Adapter and custom nodes may be fragile.
Multi-character consistency is harder than single-character consistency.
Workflow node IDs can change if the template is edited.
Local GPU resources may be constrained.
```

Mitigations:

```text
Require kuba doctor to verify ComfyUI availability and required nodes.
Keep workflow templates versioned.
Use a mapping file instead of hardcoded node IDs.
Start with two recurring characters maximum.
Use mandatory manual review after character references.
```

### Veo Or SiliconFlow Motion Clips

Abstract motion providers behind one `video_generate` phase. Prefer Veo if available; keep SiliconFlow as an alternative provider depending on access.

Paths:

```text
episodes/<episode-id>/
  video/
    motion/
      motion_0001.mp4
    manifest.json

episodes/<episode-id>/
  images/
    fallback_stills/
      motion_0001_fallback.png
```

Provider interface concept:

```text
submit_motion_job(prompt, source_image_path?, duration_sec)
  -> operation_id

poll_motion_job(operation_id)
  -> pending | completed | failed

download_motion_result(operation_id)
  -> mp4 file
```

Motion shot rules:

```text
Use exactly one 5-6 second motion shot.
Attach the motion shot to one scene.
Prefer wide/action shot over close face shot.
Strip or ignore generated video audio.
Fall back to still if provider fails.
Persist operation_id immediately.
```

Risks:

```text
Rate limits and provider access may vary.
Character consistency may be weaker than stills.
Async jobs may be slow.
Some providers may not support image-to-video in the desired tier.
```

Mitigations:

```text
Use motion for action or mood, not identity-heavy closeups.
Generate a strong ComfyUI fallback still for the same beat.
Poll with bounded backoff.
Avoid duplicate jobs on resume.
```

## Environment Variables

`.env.example` should include:

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

Provider credentials belong in `.env`. Creative and render defaults belong in YAML config.

## Doctor Checks

`kuba doctor` should verify:

```text
Python available
Node available
ffmpeg and ffprobe available
Gemini API key present
ComfyUI reachable
ComfyUI workflow file exists
ComfyUI required node classes available if detectable
Kokoro model path exists
Kokoro voices path exists
Remotion dependencies installed
episode output directory writable
```

For the full vertical-slice command path, failed doctor checks should block generation. Later commands may allow scoped checks for local-only phases.

## Testing Strategy

Prioritize contracts and resume behavior over visual perfection.

Recommended layers:

```text
1. Schema tests
   Verify blueprint examples pass or fail correctly.

2. State/resume tests
   Verify completed assets are skipped.
   Verify corrupt or missing assets are regenerated.
   Verify existing video operation IDs are reused.

3. Provider adapter tests
   Use mocked Gemini/Kokoro/ComfyUI/Veo responses.
   Confirm each provider writes expected manifest records.

4. Media probe tests
   Verify WAV, PNG, and MP4 validation behavior.

5. Render smoke test
   Use tiny local fixture assets.
   Confirm Remotion can render a short preview.
```

Manual review remains required for:

```text
Character reference approval.
Recurring character recognizability.
Scene-to-beat match.
Narration continuity.
Final preview timing and fallback behavior.
```

## Implementation Milestones

```text
Milestone 1: Project shell and contracts
  - directory structure
  - config loading
  - blueprint schema
  - state and manifest models
  - doctor command skeleton

Milestone 2: Script and blueprint generation
  - Gemini structured output
  - blueprint normalization
  - schema validation
  - sample 60-90 second story plan

Milestone 3: Character references
  - ComfyUI reference generation
  - manifest records
  - manual approval checkpoint
  - regenerate single character reference

Milestone 4: Audio and still scene assets
  - Kokoro narration segments
  - ComfyUI still scenes
  - asset validation
  - resume behavior

Milestone 5: Motion shot and fallback
  - submit, poll, and download one cloud motion clip
  - persist operation ID
  - fallback still on failure
  - strip or ignore generated video audio

Milestone 6: Remotion render
  - read blueprint and manifests
  - timeline mapping
  - still image Ken Burns motion
  - motion clip insertion
  - preview render

Milestone 7: End-to-end vertical slice
  - kuba doctor
  - create episode
  - generate script
  - generate refs
  - approve refs
  - generate assets
  - validate
  - render preview
```

## Acceptance Criteria

The vertical slice is successful when:

```text
A 60-90 second 16:9 preview MP4 renders.
It contains Kokoro narration.
It uses at least 5 generated stills.
It uses 2 approved recurring character references.
Recurring characters are recognizable across their appearances.
It attempts 1 cloud motion shot.
If the cloud motion shot fails, fallback still is used.
The run can be interrupted and resumed without regenerating valid completed assets.
Validation catches missing or corrupt required files.
```

## Non-Goals For v0.1

```text
Full 15-minute episodes
Cross-episode character continuity
Batch production of many videos
Automated visual consistency scoring
Advanced voice cloning or retraining
Multi-language narration
Complex subtitle styling
4K rendering
60 fps rendering
Full web dashboard
```

## Known Risks

```text
Highest risk:
  Character consistency in multi-character scenes.

Second highest:
  Kokoro voice quality and cadence for the desired narrator style.

Third:
  Cloud video availability, rate limits, and consistency.

Fourth:
  Audio duration drift affecting scene timing.
```

The vertical slice intentionally exposes these risks early.

## Self-Review

Placeholder scan: no unresolved TBD or TODO entries remain.

Internal consistency: the architecture consistently treats Python as the orchestrator and Remotion as a deterministic renderer. `blueprint.json`, `state.json`, and manifests have separate responsibilities.

Scope check: the design is focused on one 60-90 second vertical slice and explicitly excludes full 15-minute production, batch operations, dashboard work, and advanced voice tuning.

Ambiguity check: the mandatory character-reference review, fallback behavior, render target, episode-local continuity scope, and acceptance criteria are explicit.
