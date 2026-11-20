"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Configuration settings for the application."""

    github_token: str | None = None
    github_api_url: str = "https://api.github.com"

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            github_token=os.getenv("GITHUB_TOKEN"),
        )
