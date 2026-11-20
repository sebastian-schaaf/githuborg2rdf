"""Pipeline orchestration for extracting and transforming GitHub data."""

from githuborg2rdf.clients.github import GitHubClient
from githuborg2rdf.config import Settings
from githuborg2rdf.models import Contributor


def harvest_contributors(
    organization: str,
    client: GitHubClient,
) -> list[Contributor]:
    contributors_by_login: dict[str, Contributor] = {}

    repositories = client.list_repositories(organization)

    for repository in repositories:
        contributors = client.list_contributors(repository)

        for contributor in contributors:
            existing = contributors_by_login.get(contributor.login)

            if existing is None:
                contributors_by_login[contributor.login] = contributor
                continue

            existing.repositories.update(contributor.repositories)
            existing.contributions += contributor.contributions

    return sorted(
        contributors_by_login.values(),
        key=lambda contributor: contributor.login.lower(),
    )


def run_harvest(organization: str) -> list[Contributor]:
    settings = Settings.from_environment()
    client = GitHubClient(settings)

    return harvest_contributors(organization, client)
