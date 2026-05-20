from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class PhaseStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_REVIEW = "waiting_for_review"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    FALLBACK_USED = "fallback_used"


class EpisodeState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phases: dict[str, PhaseStatus] = Field(default_factory=dict)
    operation_ids: dict[str, str] = Field(default_factory=dict)
    retry_counts: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

    @classmethod
    def new(cls) -> "EpisodeState":
        return cls()

    def set_phase(self, name: str, status: PhaseStatus) -> None:
        self.phases[name] = status

    def save(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "EpisodeState":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


class ManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    blueprint_ref: str
    relative_path: str
    status: PhaseStatus
    provider: str


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[ManifestEntry] = Field(default_factory=list)

    def save(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def by_asset_id(self, asset_id: str) -> ManifestEntry:
        for entry in self.entries:
            if entry.asset_id == asset_id:
                return entry
        raise KeyError(asset_id)
