from pathlib import Path
from typing import Annotated

import typer

from kuba.doctor import run_python_check
from kuba.phases.audio_generate import generate_audio
from kuba.phases.character_refs import approve_refs, generate_refs
from kuba.phases.episode_create import create_episode
from kuba.phases.image_generate import generate_images
from kuba.phases.resume import resume_episode
from kuba.phases.script_generate import generate_script
from kuba.phases.validate_assets import validate_assets
from kuba.phases.video_generate import generate_video
from kuba.providers.fake import (
    FailingFakeVideoProvider,
    FakeAudioProvider,
    FakeImageProvider,
    FakeScriptProvider,
)

app = typer.Typer(name="kuba", help="Kuba folktale video pipeline.")
episode_app = typer.Typer(help="Create and manage episodes.")
script_app = typer.Typer(help="Generate episode scripts.")
refs_app = typer.Typer(help="Generate and approve character references.")
assets_app = typer.Typer(help="Generate and validate media assets.")

app.add_typer(episode_app, name="episode")
app.add_typer(script_app, name="script")
app.add_typer(refs_app, name="refs")
app.add_typer(assets_app, name="assets")


@app.callback()
def main() -> None:
    """Kuba folktale video pipeline."""


@app.command()
def doctor(
    check: Annotated[
        str,
        typer.Option("--check", help="Run one doctor check."),
    ],
) -> None:
    if check != "python":
        typer.echo("Only --check python is implemented.", err=True)
        raise typer.Exit(1)

    typer.echo(run_python_check())


@episode_app.command("create")
def episode_create(
    output_root: Annotated[Path, typer.Option("--output-root")],
    title: Annotated[str, typer.Option("--title")],
) -> None:
    episode_root = create_episode(output_root, title)
    typer.echo(episode_root)


@script_app.command("generate")
def script_generate(
    episode: Path,
    fake: Annotated[bool, typer.Option("--fake")] = False,
) -> None:
    if not fake:
        _fake_required()

    generate_script(episode, FakeScriptProvider())
    typer.echo(episode / "blueprint.json")


@refs_app.command("generate")
def refs_generate(
    episode: Path,
    fake: Annotated[bool, typer.Option("--fake")] = False,
) -> None:
    if not fake:
        _fake_required()

    generated_paths = generate_refs(episode, FakeImageProvider())
    for path in generated_paths:
        typer.echo(path)


@refs_app.command("approve")
def refs_approve(episode: Path) -> None:
    approve_refs(episode)
    typer.echo("references approved")


@assets_app.command("generate")
def assets_generate(
    episode: Path,
    fake: Annotated[bool, typer.Option("--fake")] = False,
) -> None:
    if not fake:
        _fake_required()

    image_provider = FakeImageProvider()
    generate_audio(episode, FakeAudioProvider())
    generate_images(episode, image_provider)
    generate_video(episode, FailingFakeVideoProvider(), image_provider)
    typer.echo("assets generated")


@assets_app.command("validate")
def assets_validate(episode: Path) -> None:
    report = validate_assets(episode)
    if report.ok:
        typer.echo("assets valid")
        return

    typer.echo("assets invalid")
    for error in report.errors:
        typer.echo(error)
    raise typer.Exit(1)


@app.command()
def resume(
    episode: Path,
    fake: Annotated[bool, typer.Option("--fake")] = False,
) -> None:
    if not fake:
        _fake_required()

    resume_episode(
        episode,
        audio_provider=FakeAudioProvider(),
        image_provider=FakeImageProvider(),
        video_provider=FailingFakeVideoProvider(),
    )
    typer.echo("episode resumed")


def _fake_required() -> None:
    typer.echo("Real providers are not implemented yet; pass --fake.")
    raise typer.Exit(1)
