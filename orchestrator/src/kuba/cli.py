from pathlib import Path
from typing import Annotated

import typer

from kuba.doctor import run_doctor_check
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
from kuba.providers.comfyui import ComfyUIImageProvider
from kuba.providers.gemini import GeminiScriptProvider
from kuba.providers.kokoro import KokoroAudioProvider
from kuba.providers.siliconflow import SiliconFlowVideoProvider
from kuba.providers.veo import GeminiVeoVideoProvider

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
    try:
        result = run_doctor_check(check)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)

    typer.echo(f"{result.name}: {result.message}")
    if not result.ok:
        raise typer.Exit(1)


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
    provider: Annotated[str, typer.Option("--provider")] = "",
) -> None:
    selected = "fake" if fake else provider
    if not selected:
        typer.echo("Choose --fake or --provider gemini.")
        raise typer.Exit(1)
    script_provider = _build_script_provider(selected)
    generate_script(episode, script_provider)
    typer.echo(episode / "blueprint.json")


@refs_app.command("generate")
def refs_generate(
    episode: Path,
    fake: Annotated[bool, typer.Option("--fake")] = False,
    provider: Annotated[str, typer.Option("--provider")] = "",
    workflow: Annotated[Path | None, typer.Option("--workflow")] = None,
    workflow_map: Annotated[Path | None, typer.Option("--workflow-map")] = None,
    comfy_url: Annotated[str, typer.Option("--comfy-url")] = "http://127.0.0.1:8188",
) -> None:
    selected = "fake" if fake else provider
    if not selected:
        typer.echo("Choose --fake or --provider comfy.")
        raise typer.Exit(1)
    image_provider = _build_image_provider(
        selected,
        workflow=workflow,
        workflow_map=workflow_map,
        comfy_url=comfy_url,
    )
    generated_paths = generate_refs(episode, image_provider)
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
    audio_provider: Annotated[str, typer.Option("--audio-provider")] = "",
    image_provider_name: Annotated[str, typer.Option("--image-provider")] = "",
    video_provider_name: Annotated[str, typer.Option("--video-provider")] = "",
    workflow: Annotated[Path | None, typer.Option("--workflow")] = None,
    workflow_map: Annotated[Path | None, typer.Option("--workflow-map")] = None,
    comfy_url: Annotated[str, typer.Option("--comfy-url")] = "http://127.0.0.1:8188",
) -> None:
    if fake:
        audio_provider = "fake"
        image_provider_name = "fake"
        video_provider_name = "fake-failing"
    if not audio_provider or not image_provider_name or not video_provider_name:
        typer.echo("Choose --fake or all of --audio-provider, --image-provider, and --video-provider.")
        raise typer.Exit(1)

    image_provider = _build_image_provider(
        image_provider_name,
        workflow=workflow,
        workflow_map=workflow_map,
        comfy_url=comfy_url,
    )
    generate_audio(episode, _build_audio_provider(audio_provider))
    generate_images(episode, image_provider)
    generate_video(episode, _build_video_provider(video_provider_name), image_provider)
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
    audio_provider: Annotated[str, typer.Option("--audio-provider")] = "",
    image_provider_name: Annotated[str, typer.Option("--image-provider")] = "",
    video_provider_name: Annotated[str, typer.Option("--video-provider")] = "",
) -> None:
    if fake:
        audio_provider = "fake"
        image_provider_name = "fake"
        video_provider_name = "fake-failing"
    if not audio_provider or not image_provider_name or not video_provider_name:
        typer.echo("Choose --fake or all of --audio-provider, --image-provider, and --video-provider.")
        raise typer.Exit(1)

    resume_episode(
        episode,
        audio_provider=_build_audio_provider(audio_provider),
        image_provider=_build_image_provider(image_provider_name),
        video_provider=_build_video_provider(video_provider_name),
    )
    typer.echo("episode resumed")


def _build_script_provider(provider: str):
    if provider == "fake":
        return FakeScriptProvider()
    if provider == "gemini":
        return GeminiScriptProvider()
    _provider_error("script", provider, ["fake", "gemini"])


def _build_image_provider(
    provider: str,
    *,
    workflow: Path | None = None,
    workflow_map: Path | None = None,
    comfy_url: str = "http://127.0.0.1:8188",
):
    if provider == "fake":
        return FakeImageProvider()
    if provider in {"comfy", "comfyui"}:
        if workflow is None or workflow_map is None:
            typer.echo("ComfyUI provider requires --workflow and --workflow-map.")
            raise typer.Exit(1)
        from kuba.providers.comfyui import ComfyUIClient

        return ComfyUIImageProvider(
            workflow_path=workflow,
            workflow_map_path=workflow_map,
            client=ComfyUIClient(comfy_url),
        )
    _provider_error("image", provider, ["fake", "comfy"])


def _build_audio_provider(provider: str):
    if provider == "fake":
        return FakeAudioProvider()
    if provider == "kokoro":
        import os

        return KokoroAudioProvider(
            model_path=os.environ.get("KOKORO_MODEL_PATH"),
            voices_path=os.environ.get("KOKORO_VOICES_PATH"),
        )
    _provider_error("audio", provider, ["fake", "kokoro"])


def _build_video_provider(provider: str):
    if provider in {"fake", "fake-failing"}:
        return FailingFakeVideoProvider()
    if provider == "veo":
        return GeminiVeoVideoProvider()
    if provider == "siliconflow":
        return SiliconFlowVideoProvider()
    _provider_error("video", provider, ["fake-failing", "veo", "siliconflow"])


def _provider_error(kind: str, provider: str, choices: list[str]) -> None:
    typer.echo(
        f"Unknown {kind} provider '{provider}'. Use --provider or provider-specific "
        f"options with one of: {', '.join(choices)}."
    )
    raise typer.Exit(1)
