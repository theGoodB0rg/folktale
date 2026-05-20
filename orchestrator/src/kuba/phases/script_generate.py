import json
from pathlib import Path

from kuba.blueprint.loader import load_blueprint
from kuba.providers.base import ScriptProvider
from kuba.state.episode_state import EpisodeState, PhaseStatus


def generate_script(episode_root: Path, provider: ScriptProvider) -> None:
    source_markdown = (episode_root / "script" / "source.md").read_text(encoding="utf-8")
    generated_script = provider.generate_script(source_markdown)

    script_path = episode_root / "script" / "generated_script.json"
    blueprint_path = episode_root / "blueprint.json"
    payload = json.dumps(generated_script, indent=2)
    script_path.write_text(payload, encoding="utf-8")
    blueprint_path.write_text(payload, encoding="utf-8")

    load_blueprint(blueprint_path)

    state_path = episode_root / "state.json"
    state = EpisodeState.load(state_path)
    state.set_phase("script_generate", PhaseStatus.COMPLETED)
    state.save(state_path)
