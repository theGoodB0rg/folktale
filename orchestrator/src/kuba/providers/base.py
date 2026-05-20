from typing import Any, Protocol


class ScriptProvider(Protocol):
    def generate_script(self, source_markdown: str, episode_id: str) -> dict[str, Any]:
        """Return a blueprint-compatible script payload."""


class ImageProvider(Protocol):
    provider_name: str

    def generate_image(self, episode_root: str, relative_path: str, seed_text: str) -> str:
        """Write an image for a blueprint-relative path and return its absolute path."""
