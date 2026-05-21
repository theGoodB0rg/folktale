import hashlib
import math
from pathlib import Path
import wave

from PIL import Image

from kuba.paths import resolve_episode_path


class FakeScriptProvider:
    def generate_script(self, source_markdown: str, episode_id: str) -> dict[str, object]:
        title = next(
            (line.strip("# ").strip() for line in source_markdown.splitlines() if line.strip()),
            "Untitled Episode",
        )
        scene_ids = [f"scene_{index:04d}" for index in range(1, 7)]
        scene_bounds = [(0, 12), (12, 24), (24, 38), (38, 52), (52, 65), (65, 78)]

        return {
            "schema_version": "0.1",
            "episode": {
                "id": episode_id,
                "title": title,
                "duration_sec": 78,
                "format": "vertical_slice",
            },
            "render": {
                "fps": 30,
                "preview": {"width": 720, "height": 1280},
                "final": {"width": 1080, "height": 1920},
                "audio": {"mode": "narration_only", "normalize": True},
            },
            "style": {
                "visual_style": "cinematic Kuba folktale vertical short",
                "palette": "river clay, raffia gold, indigo night, forest green",
                "negative_prompt": "watermark, text, logo, distorted faces",
            },
            "characters": [
                {
                    "id": "protagonist",
                    "role": "protagonist",
                    "display_name": "Nia",
                    "consistency_scope": "episode",
                    "reference_image_path": "images/characters/protagonist_ref.png",
                    "identity_lock": {"priority": "strict", "face": "required"},
                    "identity_prompt": {
                        "age": "young villager",
                        "wardrobe": "woven raffia sash and blue wrap",
                    },
                    "flexibility": {"pose": "flexible", "expression": "story beat dependent"},
                },
                {
                    "id": "river_spirit",
                    "role": "mystic",
                    "display_name": "River Spirit",
                    "consistency_scope": "episode",
                    "reference_image_path": "images/characters/river_spirit_ref.png",
                    "identity_lock": {"priority": "strict", "silhouette": "required"},
                    "identity_prompt": {
                        "presence": "glowing elder figure formed from river mist",
                        "wardrobe": "pearl shells and dark woven cloth",
                    },
                    "flexibility": {"pose": "flexible", "opacity": "ethereal"},
                },
            ],
            "narration": {
                "voice_profile": "config/voices/narrator.yaml",
                "segments": [
                    {
                        "id": f"seg_{index:04d}",
                        "scene_id": scene_id,
                        "text": text,
                        "start_sec": start,
                        "target_duration_sec": end - start,
                        "audio_path": f"audio/narration/seg_{index:04d}.wav",
                    }
                    for index, ((start, end), scene_id, text) in enumerate(
                        zip(
                            scene_bounds,
                            scene_ids,
                            [
                                "At dawn, Nia found the river lower than any elder remembered.",
                                "Her grandmother spoke of a debt promised before Nia was born.",
                                "Nia carried a carved calabash to the oldest bend in the water.",
                                "Mist rose, and the river spirit asked for courage instead of gold.",
                                "Nia returned what the village had taken and sang the old apology.",
                                "By sunset, the river flowed again, carrying the promise forward.",
                            ],
                        ),
                        start=1,
                    )
                ],
            },
            "scenes": [
                {
                    "id": scene_id,
                    "type": "motion" if scene_id == "scene_0004" else "still",
                    "start_sec": start,
                    "end_sec": end,
                    "beat": beat,
                    "characters_present": characters_present,
                    "identity_lock": identity_lock,
                    "visual_prompt": visual_prompt,
                    "asset_path": f"images/scenes/{scene_id}.png",
                    "camera_motion": camera_motion,
                    "transition_out": "crossfade",
                }
                for (start, end), scene_id, beat, characters_present, identity_lock, visual_prompt, camera_motion in zip(
                    scene_bounds,
                    scene_ids,
                    [
                        "The riverbed is exposed at dawn.",
                        "The debt is named by the family elder.",
                        "Nia approaches the sacred bend.",
                        "The river spirit appears in the mist.",
                        "The village makes amends.",
                        "The river returns at sunset.",
                    ],
                    [
                        ["protagonist"],
                        ["protagonist"],
                        ["protagonist"],
                        ["protagonist", "river_spirit"],
                        ["protagonist", "river_spirit"],
                        ["protagonist"],
                    ],
                    [
                        {"protagonist": "strict"},
                        {"protagonist": "strict"},
                        {"protagonist": "strict"},
                        {"protagonist": "strict", "river_spirit": "strict"},
                        {"protagonist": "strict", "river_spirit": "strict"},
                        {"protagonist": "strict"},
                    ],
                    [
                        {"environment": "wide dry river at dawn, Kuba village beyond reeds"},
                        {"environment": "mud courtyard with carved calabash and woven mats"},
                        {"environment": "narrow river bend under raffia palms"},
                        {"environment": "misty water surface with glowing spirit silhouette"},
                        {"environment": "villagers beside returning current, reflective water"},
                        {"environment": "sunset river full again, warm reflections"},
                    ],
                    [
                        {"type": "slow_push_in", "intensity": 0.12},
                        {"type": "locked_off", "intensity": 0},
                        {"type": "slow_pan", "intensity": 0.16},
                        {"type": "mist_reveal", "intensity": 0.25},
                        {"type": "gentle_pull_back", "intensity": 0.14},
                        {"type": "slow_push_in", "intensity": 0.1},
                    ],
                )
            ],
            "motion_shots": [
                {
                    "id": "motion_0001",
                    "scene_id": "scene_0004",
                    "provider": "fake",
                    "duration_sec": 6,
                    "prompt": "mist curls upward as the river spirit forms above the water",
                    "source_image_path": "images/scenes/scene_0004.png",
                    "asset_path": "video/motion/motion_0001.mp4",
                    "fallback_asset_path": "images/fallback_stills/motion_0001_fallback.png",
                    "audio_policy": "strip",
                }
            ],
            "validation": {
                "require_character_review": True,
                "required_assets": {
                    "character_refs": 2,
                    "still_scenes_min": 5,
                    "motion_shots": 1,
                    "narration_segments_min": 6,
                },
            },
        }


class FakeImageProvider:
    provider_name = "fake"

    def generate_image(
        self,
        episode_root: str,
        relative_path: str,
        seed_text: str,
        reference_image_path: str | None = None,
    ) -> str:
        output_path = resolve_episode_path(Path(episode_root), relative_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256(f"{relative_path}:{seed_text}".encode("utf-8")).digest()
        base_color = (digest[0], digest[1], digest[2])
        accent_color = (digest[3], digest[4], digest[5])

        image = Image.new("RGB", (64, 64), base_color)
        pixels = image.load()
        for y in range(64):
            for x in range(64):
                if (x + y + digest[(x + y) % len(digest)]) % 11 == 0:
                    pixels[x, y] = accent_color

        image.save(output_path, format="PNG")
        return str(output_path)


class FakeAudioProvider:
    provider_name = "fake"

    def generate_audio(
        self,
        episode_root: str,
        relative_path: str,
        text: str,
        duration_sec: float,
    ) -> str:
        output_path = resolve_episode_path(Path(episode_root), relative_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        frame_rate = 8000
        frame_count = max(1, int(duration_sec * frame_rate))
        digest = hashlib.sha256(f"{relative_path}:{text}".encode("utf-8")).digest()
        frequency = 220 + digest[0]
        amplitude = 16000

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(frame_rate)
            frames = bytearray()
            for index in range(frame_count):
                sample = int(
                    amplitude * math.sin(2 * math.pi * frequency * index / frame_rate)
                )
                frames.extend(sample.to_bytes(2, byteorder="little", signed=True))
            wav_file.writeframes(bytes(frames))

        return str(output_path)


class FailingFakeVideoProvider:
    provider_name = "fake-failing"

    def generate_video(
        self,
        episode_root: str,
        relative_path: str,
        source_image_path: str,
        prompt: str,
        duration_sec: float,
    ) -> str:
        raise RuntimeError("fake motion generation failed")
