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

    total_audio = sum(
        float(item.get("actual_duration_sec", item["target_duration_sec"]))
        for item in narration
    )
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
        issues.append(
            f"narration coverage too low: {coverage:.0%}; expected at least 72%"
        )
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
