import json
import os
from pathlib import Path
import socket
import subprocess
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

from kuba.blueprint.loader import load_blueprint
from kuba.mode import RunMode, normalize_mode
from kuba.phases.validate_assets import validate_assets
from kuba.state.episode_state import EpisodeState, PhaseStatus


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def render_episode(
    episode_root: Path,
    *,
    quality: str = "preview",
    mode: RunMode = "dev",
    remotion_root: Path | None = None,
) -> Path:
    run_mode = normalize_mode(mode)
    report = validate_assets(episode_root, mode=run_mode)
    if not report.ok:
        raise RuntimeError("asset validation failed before render: " + "; ".join(report.errors))

    blueprint = load_blueprint(episode_root / "blueprint.json")
    output_path = episode_root / "render" / f"{quality}.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    port = _find_free_port()
    server_root = episode_root.resolve().parent
    episode_slug = episode_root.resolve().name

    server = HTTPServer(
        ("127.0.0.1", port),
        lambda *a, **kw: SimpleHTTPRequestHandler(*a, directory=str(server_root), **kw),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        episode_url = f"http://127.0.0.1:{port}/{episode_slug}/"
        props_path = episode_root / "render" / f"{quality}.props.json"
        props_path.write_text(
            json.dumps(
                {
                    "blueprint": blueprint.model_dump(mode="json"),
                    "episodeRoot": episode_url,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        package_root = remotion_root or Path(__file__).resolve().parents[4] / "remotion"
        npx = "npx.cmd" if os.name == "nt" else "npx"
        command = [
            npx,
            "remotion",
            "render",
            "src/Root.tsx",
            "FolktaleEpisode",
            str(output_path),
            f"--props={props_path}",
        ]
        subprocess.run(command, cwd=package_root, check=True)
    finally:
        server.shutdown()

    if not output_path.exists():
        raise RuntimeError(f"Remotion did not write render output: {output_path}")

    state_path = episode_root / "state.json"
    state = EpisodeState.load(state_path)
    state.set_phase("render", PhaseStatus.COMPLETED)
    state.save(state_path)
    return output_path
