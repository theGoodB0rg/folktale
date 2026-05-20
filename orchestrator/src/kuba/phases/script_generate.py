import tempfile
from pathlib import Path

from kuba.blueprint.schema import Blueprint
from kuba.providers.base import ScriptProvider
from kuba.state.episode_state import EpisodeState, PhaseStatus


def generate_script(episode_root: Path, provider: ScriptProvider) -> None:
    source_markdown = (episode_root / "script" / "source.md").read_text(encoding="utf-8")
    generated_script = provider.generate_script(source_markdown, episode_root.name)
    blueprint = Blueprint.model_validate(generated_script)

    script_path = episode_root / "script" / "generated_script.json"
    blueprint_path = episode_root / "blueprint.json"
    payload = blueprint.model_dump_json(indent=2)
    _atomic_write_text(script_path, payload)
    _atomic_write_text(blueprint_path, payload)

    state_path = episode_root / "state.json"
    state = EpisodeState.load(state_path)
    state.set_phase("script_generate", PhaseStatus.COMPLETED)
    state.save(state_path)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        temp_path.replace(path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
