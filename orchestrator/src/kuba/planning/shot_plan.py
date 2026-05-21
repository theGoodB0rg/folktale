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
        CHARACTER_LANGUAGE.get(character_id, character_id)
        for character_id in characters
    )
    anti_portrait = (
        "not a portrait, not a studio portrait, not a single centered headshot, "
        "show story action and changing setting"
    )
    return (
        f"{shot_text}. Story beat: {beat}. Environment: {environment}. "
        f"Characters: {character_text}. {anti_portrait}."
    )
