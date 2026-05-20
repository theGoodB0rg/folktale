import os
from pathlib import Path

import pytest

from kuba.doctor import check_comfy, run_doctor_check


def test_local_comfy_doctor_when_enabled():
    if os.environ.get("KUBA_RUN_LOCAL_INTEGRATION") != "1":
        pytest.skip("set KUBA_RUN_LOCAL_INTEGRATION=1 to run local service checks")

    result = check_comfy()

    assert result.ok, result.message


def test_local_kokoro_paths_when_enabled():
    if os.environ.get("KUBA_RUN_LOCAL_INTEGRATION") != "1":
        pytest.skip("set KUBA_RUN_LOCAL_INTEGRATION=1 to run local service checks")

    result = run_doctor_check("kokoro")

    assert result.ok, result.message


def test_local_gemini_key_when_enabled():
    if os.environ.get("KUBA_RUN_LOCAL_INTEGRATION") != "1":
        pytest.skip("set KUBA_RUN_LOCAL_INTEGRATION=1 to run local service checks")

    result = run_doctor_check("gemini")

    assert result.ok, result.message
