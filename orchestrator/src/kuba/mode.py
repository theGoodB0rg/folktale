from typing import Literal


RunMode = Literal["dev", "production"]


FAKE_PROVIDER_NAMES = {"fake", "fake-failing"}


def normalize_mode(mode: str | None) -> RunMode:
    if mode in {None, "", "dev", "test"}:
        return "dev"
    if mode == "production":
        return "production"
    raise ValueError(f"unknown mode: {mode}")


def is_fake_provider(provider_name: str) -> bool:
    return provider_name in FAKE_PROVIDER_NAMES
