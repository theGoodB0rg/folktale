from pathlib import Path

import pytest

from kuba.state.episode_state import EpisodeState, Manifest, ManifestEntry, PhaseStatus
from kuba.state.idempotency import should_skip_asset


def test_state_round_trips_phase_and_operation_id(tmp_path: Path):
    path = tmp_path / "state.json"
    state = EpisodeState.new()
    state.set_phase("video_generate", PhaseStatus.RUNNING)
    state.operation_ids["motion_0001"] = "operations/123"
    state.save(path)

    loaded = EpisodeState.load(path)

    assert loaded.phases["video_generate"] == PhaseStatus.RUNNING
    assert loaded.operation_ids["motion_0001"] == "operations/123"


def test_manifest_round_trips_completed_entry(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest = Manifest(
        entries=[
            ManifestEntry(
                asset_id="seg_0001",
                blueprint_ref="seg_0001",
                relative_path="audio/narration/seg_0001.wav",
                status="completed",
                provider="fake",
            )
        ]
    )
    manifest.save(manifest_path)

    loaded = Manifest.load(manifest_path)

    assert loaded.by_asset_id("seg_0001").relative_path == "audio/narration/seg_0001.wav"


def test_should_skip_asset_requires_manifest_and_probe_success(tmp_path: Path):
    existing = tmp_path / "asset.wav"
    existing.write_text("fake", encoding="utf-8")
    entry = ManifestEntry(
        asset_id="seg_0001",
        blueprint_ref="seg_0001",
        relative_path="asset.wav",
        status="completed",
        provider="fake",
    )

    assert should_skip_asset(tmp_path, entry, lambda path: path.exists()) is True
    assert should_skip_asset(tmp_path, entry, lambda path: False) is False


def test_should_skip_asset_returns_false_for_non_completed_status(tmp_path: Path):
    existing = tmp_path / "asset.wav"
    existing.write_text("fake", encoding="utf-8")
    entry = ManifestEntry(
        asset_id="seg_0001",
        blueprint_ref="seg_0001",
        relative_path="asset.wav",
        status="running",
        provider="fake",
    )

    assert should_skip_asset(tmp_path, entry, lambda path: path.exists()) is False


def test_should_skip_asset_returns_false_for_path_escape(tmp_path: Path):
    outside = tmp_path.parent / "outside.wav"
    outside.write_text("fake", encoding="utf-8")
    entry = ManifestEntry(
        asset_id="seg_0001",
        blueprint_ref="seg_0001",
        relative_path="../outside.wav",
        status="completed",
        provider="fake",
    )

    assert should_skip_asset(tmp_path, entry, lambda path: path.exists()) is False


def test_manifest_by_asset_id_raises_key_error_for_missing_asset():
    manifest = Manifest(entries=[])

    with pytest.raises(KeyError):
        manifest.by_asset_id("missing")
