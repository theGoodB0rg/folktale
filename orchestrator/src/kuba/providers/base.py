from typing import Any, Protocol


class ScriptProvider(Protocol):
    def generate_script(self, source_markdown: str) -> dict[str, Any]:
        """Return a blueprint-compatible script payload."""
