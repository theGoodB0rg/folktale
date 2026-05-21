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
