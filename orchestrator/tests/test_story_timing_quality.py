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
