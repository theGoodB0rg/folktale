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
                    "id": "child",
                    "role": "protagonist",
                    "display_name": "Nia",
                    "consistency_scope": "episode",
                    "reference_image_path": "images/characters/child_ref.png",
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
                        ["child"],
                        ["child"],
                        ["child"],
                        ["child", "river_spirit"],
                        ["child", "river_spirit"],
                        ["child"],
                    ],
                    [
                        {"child": "strict"},
                        {"child": "strict"},
                        {"child": "strict"},
                        {"child": "strict", "river_spirit": "strict"},
                        {"child": "strict", "river_spirit": "strict"},
                        {"child": "strict"},
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
