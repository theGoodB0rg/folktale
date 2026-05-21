# Watchable Production Proof Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a 60-90 second production proof video that works as a story when muted and as narration when heard, with no long silent gaps, no single-image feel, and recognizable recurring characters.

**Architecture:** Split the fix into four maintainable boundaries: blueprint pacing validation, shot planning, provider prompt construction, and QA scoring. The pipeline should reject weak proof artifacts before render completion is claimed, instead of relying on manual eyeballing after the fact.

**Tech Stack:** Python orchestrator, Pydantic blueprint schema, pytest, ComfyUI image generation, Kokoro audio, SiliconFlow I2V, Remotion render, ffprobe/Pillow media validation.

---

## File Structure

- Modify `orchestrator/src/kuba/blueprint/schema.py`
  - Add optional fields for richer scene and motion planning without breaking existing fixture files.
- Create `orchestrator/src/kuba/quality/story_timing.py`
  - Compute narration coverage, silence gaps, scene hold durations, and motion coverage from blueprint plus manifests.
- Create `orchestrator/src/kuba/quality/visual_diversity.py`
  - Compute low-cost image diversity signals: perceptual-ish thumbnail distance, repeated dominant crop warnings, and scene/reference similarity warnings.
- Modify `orchestrator/src/kuba/phases/validate_assets.py`
  - In production mode, fail artifacts that are technically valid but not watchable enough.
- Modify `orchestrator/src/kuba/phases/image_generate.py`
  - Build scene prompts from shot intent, composition, action, environment, and character constraints.
- Create `orchestrator/src/kuba/planning/shot_plan.py`
  - Generate deterministic shot plans from a blueprint: wide/action/insert/reaction/mystic reveal, with reference-character guidance.
- Modify `orchestrator/src/kuba/providers/comfyui.py`
  - Support `reference_strength` and composition-aware positive prompts.
- Modify `orchestrator/src/kuba/providers/siliconflow.py`
  - Keep I2V JPEG submission, but support multiple motion shots and short provider-friendly prompts.
- Modify `remotion/src/components/SceneStill.tsx`
  - Add stronger deterministic still motion: pan, push, pull, parallax-like crop movement where possible.
- Modify `remotion/src/components/NarrationAudioLayer.tsx`
  - Do not stretch audio, but allow blueprint validation to enforce narration coverage before render.
- Modify `config/blueprints/vertical_slice_fixture.json`
  - Replace the current underwritten fixture with a proper 60-90 second proof script and visually distinct beats.
- Create or modify tests:
  - `orchestrator/tests/test_story_timing_quality.py`
  - `orchestrator/tests/test_visual_diversity_quality.py`
  - `orchestrator/tests/test_image_prompt_planning.py`
  - `orchestrator/tests/test_vertical_slice_integration.py`

---

### Task 1: Add Production Story Timing Gates

**Files:**
- Create: `orchestrator/src/kuba/quality/story_timing.py`
- Modify: `orchestrator/src/kuba/phases/validate_assets.py`
- Test: `orchestrator/tests/test_story_timing_quality.py`

- [ ] **Step 1: Write failing tests for silence and coverage**

Create `orchestrator/tests/test_story_timing_quality.py`:

```python
from kuba.quality.story_timing import analyze_story_timing


def test_story_timing_flags_sparse_narration():
    blueprint = {
        "episode_duration_sec": 78.0,
        "narration": [
            {"id": "seg_1", "start_sec": 0.0, "target_duration_sec": 12.0, "actual_duration_sec": 4.0},
            {"id": "seg_2", "start_sec": 12.0, "target_duration_sec": 12.0, "actual_duration_sec": 4.0},
        ],
        "scenes": [
            {"id": "scene_1", "start_sec": 0.0, "end_sec": 39.0, "type": "still"},
            {"id": "scene_2", "start_sec": 39.0, "end_sec": 78.0, "type": "still"},
        ],
        "motion": [],
    }

    report = analyze_story_timing(blueprint)

    assert report.ok is False
    assert any("narration coverage" in issue for issue in report.issues)
    assert any("silent gap" in issue for issue in report.issues)
    assert any("still hold" in issue for issue in report.issues)


def test_story_timing_accepts_dense_watchable_plan():
    blueprint = {
        "episode_duration_sec": 72.0,
        "narration": [
            {"id": "seg_1", "start_sec": 0.0, "target_duration_sec": 10.0, "actual_duration_sec": 8.5},
            {"id": "seg_2", "start_sec": 10.0, "target_duration_sec": 10.0, "actual_duration_sec": 8.5},
            {"id": "seg_3", "start_sec": 20.0, "target_duration_sec": 10.0, "actual_duration_sec": 8.5},
            {"id": "seg_4", "start_sec": 30.0, "target_duration_sec": 10.0, "actual_duration_sec": 8.5},
            {"id": "seg_5", "start_sec": 40.0, "target_duration_sec": 10.0, "actual_duration_sec": 8.5},
            {"id": "seg_6", "start_sec": 50.0, "target_duration_sec": 10.0, "actual_duration_sec": 8.5},
            {"id": "seg_7", "start_sec": 60.0, "target_duration_sec": 12.0, "actual_duration_sec": 9.0},
        ],
        "scenes": [
            {"id": "scene_1", "start_sec": 0.0, "end_sec": 8.0, "type": "still"},
            {"id": "scene_2", "start_sec": 8.0, "end_sec": 16.0, "type": "motion"},
            {"id": "scene_3", "start_sec": 16.0, "end_sec": 24.0, "type": "still"},
            {"id": "scene_4", "start_sec": 24.0, "end_sec": 32.0, "type": "motion"},
            {"id": "scene_5", "start_sec": 32.0, "end_sec": 40.0, "type": "still"},
            {"id": "scene_6", "start_sec": 40.0, "end_sec": 48.0, "type": "motion"},
            {"id": "scene_7", "start_sec": 48.0, "end_sec": 56.0, "type": "still"},
            {"id": "scene_8", "start_sec": 56.0, "end_sec": 64.0, "type": "motion"},
            {"id": "scene_9", "start_sec": 64.0, "end_sec": 72.0, "type": "still"},
        ],
        "motion": [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}, {"id": "m4"}],
    }

    report = analyze_story_timing(blueprint)

    assert report.ok is True
    assert report.issues == []
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```powershell
cd orchestrator
python -m pytest tests/test_story_timing_quality.py -v
```

Expected: fails because `kuba.quality.story_timing` does not exist.

- [ ] **Step 3: Implement timing analyzer**

Create `orchestrator/src/kuba/quality/story_timing.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryTimingReport:
    ok: bool
    issues: list[str]
    narration_coverage: float
    longest_silent_gap_sec: float
    longest_still_hold_sec: float
    motion_scene_count: int


def analyze_story_timing(payload: dict) -> StoryTimingReport:
    duration = float(payload["episode_duration_sec"])
    narration = sorted(payload["narration"], key=lambda item: float(item["start_sec"]))
    scenes = payload["scenes"]
    motion = payload["motion"]

    total_audio = sum(float(item.get("actual_duration_sec", item["target_duration_sec"])) for item in narration)
    coverage = total_audio / duration if duration else 0.0
    longest_gap = _longest_silent_gap(narration, duration)
    longest_still = max(
        (
            float(scene["end_sec"]) - float(scene["start_sec"])
            for scene in scenes
            if scene.get("type") == "still"
        ),
        default=0.0,
    )
    motion_count = len(motion)

    issues: list[str] = []
    if coverage < 0.72:
        issues.append(f"narration coverage too low: {coverage:.0%}; expected at least 72%")
    if longest_gap > 3.0:
        issues.append(f"silent gap too long: {longest_gap:.2f}s; expected <= 3.00s")
    if longest_still > 9.0:
        issues.append(f"still hold too long: {longest_still:.2f}s; expected <= 9.00s")
    if motion_count < 3:
        issues.append(f"motion shot count too low: {motion_count}; expected at least 3")

    return StoryTimingReport(
        ok=not issues,
        issues=issues,
        narration_coverage=coverage,
        longest_silent_gap_sec=longest_gap,
        longest_still_hold_sec=longest_still,
        motion_scene_count=motion_count,
    )


def _longest_silent_gap(narration: list[dict], duration: float) -> float:
    cursor = 0.0
    longest = 0.0
    for item in narration:
        start = float(item["start_sec"])
        actual_duration = float(item.get("actual_duration_sec", item["target_duration_sec"]))
        longest = max(longest, start - cursor)
        cursor = max(cursor, start + actual_duration)
    return max(longest, duration - cursor)
```

- [ ] **Step 4: Run timing tests**

Run:

```powershell
python -m pytest tests/test_story_timing_quality.py -v
```

Expected: both tests pass.

- [ ] **Step 5: Integrate timing gate into production validation**

In `orchestrator/src/kuba/phases/validate_assets.py`, after loading blueprint and manifests, build the timing payload from:

```python
timing_payload = {
    "episode_duration_sec": blueprint.episode.duration_sec,
    "narration": [
        {
            "id": segment.id,
            "start_sec": segment.start_sec,
            "target_duration_sec": segment.target_duration_sec,
            "actual_duration_sec": audio_durations_by_asset_id.get(segment.id, segment.target_duration_sec),
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
```

Then:

```python
from kuba.quality.story_timing import analyze_story_timing

if run_mode == "production":
    timing_report = analyze_story_timing(timing_payload)
    errors.extend(timing_report.issues)
```

- [ ] **Step 6: Add integration assertion**

In `orchestrator/tests/test_vertical_slice_integration.py`, add:

```python
def test_production_validation_fails_sparse_story_timing(tmp_path: Path):
    episode_root = create_episode(tmp_path / "episodes", "The River's Debt")
    generate_script(episode_root, FakeScriptProvider())
    generate_refs(episode_root, FakeImageProvider())
    approve_refs(episode_root)
    generate_audio(episode_root, FakeAudioProvider())
    generate_images(episode_root, FakeImageProvider())
    generate_video(episode_root, FailingFakeVideoProvider(), FakeImageProvider())

    audio_manifest_path = episode_root / "audio" / "manifest.json"
    payload = json.loads(audio_manifest_path.read_text(encoding="utf-8"))
    for entry in payload["entries"]:
        entry["duration_sec"] = 1.0
    audio_manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    report = validate_assets(episode_root, mode="production")

    assert report.ok is False
    assert any("narration coverage" in error for error in report.errors)
```

- [ ] **Step 7: Run validation tests**

Run:

```powershell
python -m pytest tests/test_story_timing_quality.py tests/test_vertical_slice_integration.py::test_production_validation_fails_sparse_story_timing -v
```

Expected: pass.

- [ ] **Step 8: Commit**

```powershell
git add orchestrator/src/kuba/quality/story_timing.py orchestrator/src/kuba/phases/validate_assets.py orchestrator/tests/test_story_timing_quality.py orchestrator/tests/test_vertical_slice_integration.py
git commit -m "feat: reject sparse production story timing"
```

---

### Task 2: Add Shot Planning So Scenes Are Story Beats, Not Repeated Portraits

**Files:**
- Create: `orchestrator/src/kuba/planning/shot_plan.py`
- Modify: `orchestrator/src/kuba/phases/image_generate.py`
- Test: `orchestrator/tests/test_image_prompt_planning.py`

- [ ] **Step 1: Write failing prompt-planning tests**

Create `orchestrator/tests/test_image_prompt_planning.py`:

```python
from kuba.planning.shot_plan import build_scene_prompt


def test_scene_prompt_includes_composition_action_environment_and_character_role():
    prompt = build_scene_prompt(
        beat="Nia crosses a cracked riverbed with a calabash.",
        environment="wide dry river at dawn, Kuba village beyond reeds",
        characters=["protagonist"],
        shot_kind="wide_action",
    )

    assert "wide establishing story frame" in prompt
    assert "full body" in prompt
    assert "Nia crosses a cracked riverbed" in prompt
    assert "wide dry river at dawn" in prompt
    assert "preserve protagonist face and wardrobe" in prompt
    assert "not a portrait" in prompt


def test_scene_prompt_for_two_characters_mentions_both_without_portrait_bias():
    prompt = build_scene_prompt(
        beat="The river spirit rises while Nia kneels at the water.",
        environment="misty water surface with glowing spirit silhouette",
        characters=["protagonist", "river_spirit"],
        shot_kind="mystic_reveal",
    )

    assert "two-character composition" in prompt
    assert "river spirit" in prompt
    assert "Nia" in prompt
    assert "not a studio portrait" in prompt
```

- [ ] **Step 2: Run tests and confirm failure**

```powershell
cd orchestrator
python -m pytest tests/test_image_prompt_planning.py -v
```

Expected: import failure.

- [ ] **Step 3: Implement shot prompt builder**

Create `orchestrator/src/kuba/planning/shot_plan.py`:

```python
from __future__ import annotations


SHOT_LANGUAGE = {
    "wide_action": "wide establishing story frame, full body, visible environment, cinematic action beat",
    "insert": "close insert shot of story object, hands and prop detail, environment still visible",
    "reaction": "medium reaction shot, character expression plus background context",
    "mystic_reveal": "two-character composition, supernatural reveal, mist and light interacting with the environment",
    "resolution": "wide resolution frame, changed environment, clear before-and-after story consequence",
}


CHARACTER_LANGUAGE = {
    "protagonist": "Nia, preserve protagonist face and wardrobe from reference",
    "river_spirit": "river spirit, preserve ethereal elder silhouette from reference",
}


def build_scene_prompt(
    *,
    beat: str,
    environment: str,
    characters: list[str],
    shot_kind: str,
) -> str:
    shot_text = SHOT_LANGUAGE.get(shot_kind, SHOT_LANGUAGE["wide_action"])
    character_text = "; ".join(
        CHARACTER_LANGUAGE.get(character_id, character_id) for character_id in characters
    )
    anti_portrait = (
        "not a portrait, not a studio portrait, not a single centered headshot, "
        "show story action and changing setting"
    )
    return (
        f"{shot_text}. Story beat: {beat}. Environment: {environment}. "
        f"Characters: {character_text}. {anti_portrait}."
    )
```

- [ ] **Step 4: Update image generation to use shot prompts**

In `orchestrator/src/kuba/phases/image_generate.py`, replace:

```python
environment = scene.visual_prompt.get("environment", str(scene.visual_prompt))
seed_text = f"{scene.beat} {environment}"
```

with:

```python
from kuba.planning.shot_plan import build_scene_prompt

environment = scene.visual_prompt.get("environment", str(scene.visual_prompt))
shot_kind = str(scene.visual_prompt.get("shot_kind", scene.camera_motion.get("type", "wide_action")))
seed_text = build_scene_prompt(
    beat=scene.beat,
    environment=environment,
    characters=list(scene.characters_present),
    shot_kind=shot_kind,
)
```

- [ ] **Step 5: Run prompt tests**

```powershell
python -m pytest tests/test_image_prompt_planning.py -v
```

Expected: pass.

- [ ] **Step 6: Run image generation regression**

```powershell
python -m pytest tests/test_vertical_slice_integration.py::test_generate_images_creates_motion_source_scene_image tests/test_real_providers.py::test_comfy_provider_submits_polls_and_downloads_image -v
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git add orchestrator/src/kuba/planning/shot_plan.py orchestrator/src/kuba/phases/image_generate.py orchestrator/tests/test_image_prompt_planning.py
git commit -m "feat: plan story-first scene prompts"
```

---

### Task 3: Add Visual Diversity QA

**Files:**
- Create: `orchestrator/src/kuba/quality/visual_diversity.py`
- Modify: `orchestrator/src/kuba/phases/validate_assets.py`
- Test: `orchestrator/tests/test_visual_diversity_quality.py`

- [ ] **Step 1: Write failing diversity tests**

Create `orchestrator/tests/test_visual_diversity_quality.py`:

```python
from pathlib import Path

from PIL import Image

from kuba.quality.visual_diversity import analyze_visual_diversity


def test_visual_diversity_flags_nearly_identical_scene_images(tmp_path: Path):
    paths = []
    for index in range(4):
        path = tmp_path / f"scene_{index}.png"
        Image.new("RGB", (64, 64), (20, 80, 120)).save(path)
        paths.append(path)

    report = analyze_visual_diversity(paths)

    assert report.ok is False
    assert any("too similar" in issue for issue in report.issues)


def test_visual_diversity_accepts_distinct_scene_images(tmp_path: Path):
    colors = [(20, 80, 120), (120, 30, 20), (30, 130, 50), (200, 180, 60)]
    paths = []
    for index, color in enumerate(colors):
        path = tmp_path / f"scene_{index}.png"
        Image.new("RGB", (64, 64), color).save(path)
        paths.append(path)

    report = analyze_visual_diversity(paths)

    assert report.ok is True
```

- [ ] **Step 2: Run tests and confirm failure**

```powershell
cd orchestrator
python -m pytest tests/test_visual_diversity_quality.py -v
```

Expected: import failure.

- [ ] **Step 3: Implement diversity analyzer**

Create `orchestrator/src/kuba/quality/visual_diversity.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageStat


@dataclass(frozen=True)
class VisualDiversityReport:
    ok: bool
    issues: list[str]
    average_pair_distance: float


def analyze_visual_diversity(paths: list[Path]) -> VisualDiversityReport:
    signatures = [_signature(path) for path in paths]
    distances: list[float] = []
    for left_index, left in enumerate(signatures):
        for right in signatures[left_index + 1 :]:
            distances.append(_distance(left, right))

    average = sum(distances) / len(distances) if distances else 0.0
    issues: list[str] = []
    if len(paths) >= 4 and average < 18.0:
        issues.append(f"scene images are too similar: average thumbnail distance {average:.2f}")
    return VisualDiversityReport(ok=not issues, issues=issues, average_pair_distance=average)


def _signature(path: Path) -> tuple[float, float, float]:
    image = Image.open(path).convert("RGB").resize((16, 16))
    stat = ImageStat.Stat(image)
    return tuple(float(value) for value in stat.mean[:3])


def _distance(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return sum(abs(a - b) for a, b in zip(left, right)) / 3.0
```

- [ ] **Step 4: Integrate in production validation**

In `orchestrator/src/kuba/phases/validate_assets.py`, after image paths are validated:

```python
from kuba.quality.visual_diversity import analyze_visual_diversity

if run_mode == "production":
    scene_paths = [resolve_episode_path(episode_root, scene.asset_path) for scene in blueprint.scenes]
    visual_report = analyze_visual_diversity(scene_paths)
    errors.extend(visual_report.issues)
```

- [ ] **Step 5: Run quality tests**

```powershell
python -m pytest tests/test_visual_diversity_quality.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add orchestrator/src/kuba/quality/visual_diversity.py orchestrator/src/kuba/phases/validate_assets.py orchestrator/tests/test_visual_diversity_quality.py
git commit -m "feat: reject visually repetitive production scenes"
```

---

### Task 4: Replace Fixture Blueprint With A Watchable Proof Blueprint

**Files:**
- Modify: `config/blueprints/vertical_slice_fixture.json`
- Test: `orchestrator/tests/test_env_and_fixture.py`

- [ ] **Step 1: Rewrite the fixture story structure**

Set the fixture to:

- 72 seconds total.
- 9 scenes, 8 seconds each.
- 7 narration segments with 18-25 words each.
- 4 motion shots at the turning points.
- Scene prompts include `shot_kind`.

Use this story beat map:

```json
[
  {"scene": "scene_0001", "time": "0-8", "type": "still", "shot_kind": "wide_action", "beat": "Nia sees the riverbed cracked open at dawn."},
  {"scene": "scene_0002", "time": "8-16", "type": "motion", "shot_kind": "insert", "beat": "Her calabash rolls into a dry channel and stops beside old carved stones."},
  {"scene": "scene_0003", "time": "16-24", "type": "still", "shot_kind": "reaction", "beat": "Grandmother points to the debt mark woven into Nia's blue sash."},
  {"scene": "scene_0004", "time": "24-32", "type": "motion", "shot_kind": "wide_action", "beat": "Nia runs from the village toward the sacred bend with the calabash."},
  {"scene": "scene_0005", "time": "32-40", "type": "still", "shot_kind": "insert", "beat": "Nia pours the first offering into a hollow where water should be."},
  {"scene": "scene_0006", "time": "40-48", "type": "motion", "shot_kind": "mystic_reveal", "beat": "The river spirit rises from mist in front of Nia."},
  {"scene": "scene_0007", "time": "48-56", "type": "still", "shot_kind": "reaction", "beat": "Nia chooses courage and returns the stolen river stones."},
  {"scene": "scene_0008", "time": "56-64", "type": "motion", "shot_kind": "resolution", "beat": "Water surges back through the riverbed as villagers step away."},
  {"scene": "scene_0009", "time": "64-72", "type": "still", "shot_kind": "wide_action", "beat": "At sunset Nia watches the full river carry the promise onward."}
]
```

- [ ] **Step 2: Add narration with dense coverage**

Use narration text like:

```json
[
  "At dawn, Nia stepped into the empty riverbed and found fish bones shining where water should have been.",
  "Her grandmother tied the blue sash tighter and named the debt their family had hidden for a generation.",
  "The carved calabash rolled ahead of Nia, stopping beside stones marked with the river spirit's old warning.",
  "Nia ran past the raffia palms before fear could turn her back toward the silent village.",
  "She poured the first offering into dust and promised to return what her people had taken.",
  "Mist climbed from the cracked earth, and the river spirit rose, asking for courage instead of gold.",
  "Nia carried the stolen stones home, and the water followed her song back through the valley."
]
```

- [ ] **Step 3: Validate fixture schema**

Run:

```powershell
cd orchestrator
python -m pytest tests/test_env_and_fixture.py::test_fixture_script_provider_loads_valid_blueprint_and_rewrites_episode_id -v
```

Expected: pass.

- [ ] **Step 4: Commit**

```powershell
git add config/blueprints/vertical_slice_fixture.json
git commit -m "test: make fixture blueprint watchable"
```

---

### Task 5: Generate A New QA Episode And Enforce Gates

**Files:**
- No source edits expected.
- Generated artifacts under `episodes/the-rivers-debt-watchable-qa`.

- [ ] **Step 1: Create fresh episode**

```powershell
cd orchestrator
kuba episode create --output-root ../episodes --title "The River's Debt Watchable QA"
```

Expected output path:

```text
..\episodes\the-rivers-debt-watchable-qa
```

- [ ] **Step 2: Generate fixture script**

```powershell
kuba script generate ../episodes/the-rivers-debt-watchable-qa --provider fixture --mode production --blueprint-fixture ../config/blueprints/vertical_slice_fixture.json
```

Expected: `blueprint.json` with 72 seconds, 9 scenes, 7 narration segments, 4 motion shots.

- [ ] **Step 3: Generate and review character refs**

```powershell
kuba refs generate ../episodes/the-rivers-debt-watchable-qa --provider comfy --mode production --workflow ../config/comfy/workflows/sdxl_ip_adapter_api.json --workflow-map ../config/comfy/workflows/sdxl_ip_adapter_api.map.yaml
```

Create a contact sheet and inspect it before approval.

- [ ] **Step 4: Approve refs only if they are distinct**

```powershell
kuba refs approve ../episodes/the-rivers-debt-watchable-qa
```

Do not approve if protagonist and river spirit are ambiguous or visually unusable.

- [ ] **Step 5: Generate assets**

```powershell
kuba assets generate ../episodes/the-rivers-debt-watchable-qa --mode production --audio-provider kokoro --image-provider comfy --video-provider siliconflow --workflow ../config/comfy/workflows/sdxl_ip_adapter_api.json --workflow-map ../config/comfy/workflows/sdxl_ip_adapter_api.map.yaml
```

Expected:

- 7 valid WAVs.
- 9 visually distinct scene PNGs.
- 4 real MP4 motion clips.
- No fallback still video entries in production.

- [ ] **Step 6: Run production validation**

```powershell
kuba assets validate ../episodes/the-rivers-debt-watchable-qa --mode production
```

Expected: pass only if timing, visual diversity, real media, and no-fallback rules pass.

- [ ] **Step 7: Render preview**

```powershell
kuba render ../episodes/the-rivers-debt-watchable-qa --quality preview --mode production
```

Expected: `..\episodes\the-rivers-debt-watchable-qa\render\preview.mp4`.

- [ ] **Step 8: ffprobe verification**

```powershell
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,duration -show_entries format=duration,size -of json ../episodes/the-rivers-debt-watchable-qa/render/preview.mp4
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,duration -show_entries format=duration,size -of json ../episodes/the-rivers-debt-watchable-qa/video/motion/motion_0001.mp4
```

Expected:

- Preview has H.264 video and AAC audio.
- Runtime is 60-90 seconds.
- Each motion clip is a real MP4.

- [ ] **Step 9: Human QA checklist**

Watch the preview muted first:

- Does the story progression make sense from visuals alone?
- Do scenes change composition, action, and setting?
- Does the protagonist remain recognizable without every frame becoming a portrait?
- Are there at least 4 visibly moving moments?

Then watch with audio:

- No long silent gaps.
- Narration timing feels intentional.
- Audio is human voice, not placeholders.

- [ ] **Step 10: Commit source changes only**

Generated episodes should remain uncommitted unless the repo intentionally tracks QA artifacts.

```powershell
git status --short
git add <source files only>
git commit -m "feat: enforce watchable production proof quality"
```

---

## Self-Review

Spec coverage:

- Rejects long silent gaps: Task 1.
- Rejects long static holds: Task 1.
- Avoids single-image/repeated portrait failure: Tasks 2 and 3.
- Maintains recognizable recurring characters: Task 2 keeps character reference guidance while reducing portrait bias.
- Requires real video, not fallback stills: existing production validation remains, Task 5 verifies it.
- Produces 60-90 second proof: Task 4 sets 72s fixture, Task 5 renders it.

Placeholder scan:

- No task uses TBD/TODO/later.
- Each code task includes exact files, snippets, commands, and expected results.

Type consistency:

- `analyze_story_timing()` and `analyze_visual_diversity()` return dataclass reports with `ok` and `issues`.
- `build_scene_prompt()` is used by `image_generate.py` and tested directly.

