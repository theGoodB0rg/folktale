from typing import Any, Protocol


class ScriptProvider(Protocol):
    def generate_script(self, source_markdown: str, episode_id: str) -> dict[str, Any]:
        """Return a blueprint-compatible script payload."""


class ImageProvider(Protocol):
    provider_name: str

    def generate_image(self, episode_root: str, relative_path: str, seed_text: str) -> str:
        """Write an image for a blueprint-relative path and return its absolute path."""


class AudioProvider(Protocol):
    provider_name: str

    def generate_audio(
        self,
        episode_root: str,
        relative_path: str,
        text: str,
        duration_sec: float,
    ) -> str:
        """Write narration audio for a blueprint-relative path and return its absolute path."""


class VideoProvider(Protocol):
    provider_name: str

    def generate_video(
        self,
        episode_root: str,
        relative_path: str,
        source_image_path: str,
        prompt: str,
        duration_sec: float,
    ) -> str:
        """Write a motion video for a blueprint-relative path and return its absolute path."""
