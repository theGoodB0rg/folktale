import json
from pathlib import Path

from kuba.blueprint.schema import Blueprint


class FixtureScriptProvider:
    provider_name = "fixture"

    def __init__(self, fixture_path: Path) -> None:
        self.fixture_path = fixture_path

    def generate_script(self, source_markdown: str, episode_id: str) -> dict[str, object]:
        payload = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        title = _extract_title(source_markdown)
        payload.setdefault("episode", {})["id"] = episode_id
        payload["episode"]["title"] = title
        for shot in payload.get("motion_shots", []):
            shot["provider"] = "fixture"
        blueprint = Blueprint.model_validate(payload)
        return blueprint.model_dump(mode="json")


def _extract_title(source_markdown: str) -> str:
    for line in source_markdown.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.lstrip("#").strip()
    return "Untitled Episode"
