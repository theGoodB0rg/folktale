import json
from pathlib import Path
from typing import Any

from kuba.blueprint.schema import Blueprint


def load_blueprint(path: Path) -> Blueprint:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return Blueprint.model_validate(data)
