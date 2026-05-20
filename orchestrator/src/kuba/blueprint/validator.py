from pathlib import Path

from kuba.blueprint.loader import load_blueprint
from kuba.blueprint.schema import Blueprint


def validate_blueprint_file(path: Path) -> Blueprint:
    return load_blueprint(path)
