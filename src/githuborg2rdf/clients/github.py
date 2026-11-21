"""GitHub API client functionality."""

from collections.abc import Iterator
from typing import Any

import requests

from githuborg2rdf.config import Settings
from githuborg2rdf.models import Contributor, Repository


class GitHubApiError(RuntimeError):
    """Raised when the GitHub API returns an error response."""


class GitHubClient:
    """Client for accessing the GitHub REST API."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the GitHub API client from application settings."""
        self.base_url = settings.github_api_url
        self.session = requests.Session()

        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

        if settings.github_token:
            self.session.headers["Authorization"] = f"Bearer {settings.github_token}"

    def _get_paginated(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        page = 1
        request_params = dict(params or {})
        request_params.setdefault("per_page", 100)

        while True:
            try:
                response = self.session.get(
                    f"{self.base_url}{path}",
                    params={**request_params, "page": page},
                    timeout=30,
                )
            except requests.RequestException as exc:
                raise GitHubApiError(
                    f"GitHub API request failed for {path}: {exc}"
                ) from exc

            if not response.ok:
                raise GitHubApiError(
                    f"GitHub API returned {response.status_code} for "
                    f"{response.url}: {response.text}"
                )

            items = response.json()

            if not isinstance(items, list):
                raise GitHubApiError(
                    f"Expected a list from {response.url}, "
                    f"received {type(items).__name__}"
                )

            if not items:
                break

            yield from items
            page += 1

    def list_repositories(self, organization: str) -> list[Repository]:
        repositories: list[Repository] = []

        for item in self._get_paginated(
            f"/orgs/{organization}/repos",
            params={"type": "all", "sort": "full_name"},
        ):
            repositories.append(
                Repository(
                    owner=organization,
                    name=item["name"],
                    html_url=item["html_url"],
                )
            )

        return repositories

    def list_contributors(
        self,
        repository: Repository,
    ) -> list[Contributor]:
        contributors: list[Contributor] = []

        for item in self._get_paginated(
            f"/repos/{repository.owner}/{repository.name}/contributors"
        ):
            login = item.get("login", "")
            contributor_type = item.get("type", "")

            is_bot = contributor_type.lower() == "bot" or login.endswith("[bot]")

            if is_bot:
                continue

            contributors.append(
                Contributor(
                    login=login,
                    html_url=item.get("html_url", ""),
                    contributions=item.get("contributions", 0),
                    repositories={repository.name},
                )
            )

        return contributors
