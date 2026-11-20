"""Data models used by the githuborg2rdf pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Repository:
    """Represent a GitHub repository."""

    owner: str
    name: str
    html_url: str


@dataclass
class Contributor:
    """Represent a contributor to one or more GitHub repositories."""

    login: str
    html_url: str
    contributions: int
    repositories: set[str]
    is_bot: bool = False
