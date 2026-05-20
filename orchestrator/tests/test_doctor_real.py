from pathlib import Path

from kuba.doctor import check_comfy, check_env, check_path, run_doctor_check


def test_check_env_reports_missing_without_revealing_value(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = check_env("GEMINI_API_KEY")

    assert result.ok is False
    assert result.name == "env:GEMINI_API_KEY"
    assert "missing" in result.message


def test_check_env_reports_present_without_secret(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret-value")

    result = check_env("GEMINI_API_KEY")

    assert result.ok is True
    assert "secret-value" not in result.message


def test_check_path_requires_existing_file(tmp_path: Path):
    model = tmp_path / "kokoro.onnx"
    model.write_text("model", encoding="utf-8")

    assert check_path("kokoro-model", str(model)).ok is True
    assert check_path("kokoro-model", str(tmp_path / "missing.onnx")).ok is False


def test_check_comfy_uses_system_stats_endpoint():
    def get_json(url: str, timeout_sec: float):
        assert url == "http://comfy.local/system_stats"
        assert timeout_sec == 3
        return {"system": {"os": "test"}}

    result = check_comfy("http://comfy.local", get_json=get_json)

    assert result.ok is True
    assert "reachable" in result.message


def test_run_doctor_check_supports_real_check_names(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GEMINI_API_KEY", "present")
    monkeypatch.setenv("KOKORO_MODEL_PATH", str(tmp_path / "missing.onnx"))

    assert run_doctor_check("gemini").ok is True
    assert run_doctor_check("kokoro").ok is False


def test_production_doctor_aggregates_required_checks(monkeypatch, tmp_path: Path):
    model = tmp_path / "kokoro.onnx"
    voices = tmp_path / "voices.bin"
    workflow = tmp_path / "workflow.json"
    workflow_map = tmp_path / "workflow.map.yaml"
    remotion_package = tmp_path / "remotion" / "package.json"
    for path in [model, voices, workflow, workflow_map, remotion_package]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    (tmp_path / "remotion" / "node_modules").mkdir()

    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setenv("KOKORO_MODEL_PATH", str(model))
    monkeypatch.setenv("KOKORO_VOICES_PATH", str(voices))
    monkeypatch.setenv("SILICONFLOW_API_KEY", "key")
    monkeypatch.setenv("KUBA_COMFY_WORKFLOW", str(workflow))
    monkeypatch.setenv("KUBA_COMFY_WORKFLOW_MAP", str(workflow_map))
    monkeypatch.setenv("KUBA_REMOTION_ROOT", str(tmp_path / "remotion"))
    monkeypatch.setattr("kuba.doctor.check_comfy", lambda: check_env("GEMINI_API_KEY"))
    monkeypatch.setattr("kuba.doctor._which", lambda name: f"/bin/{name}")

    result = run_doctor_check("production")

    assert result.ok is True
    assert "production checks passed" in result.message
