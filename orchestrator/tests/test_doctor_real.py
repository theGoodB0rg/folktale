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
