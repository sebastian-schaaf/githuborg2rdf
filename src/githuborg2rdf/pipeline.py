"""Pipeline orchestration for extracting and transforming GitHub data."""

from dataclasses import replace
from typing import Protocol

from githuborg2rdf.clients.datacite import DataCiteClient, DOIClient
from githuborg2rdf.clients.github import GitHubClient
from githuborg2rdf.clients.orcid import ORCIDClient, OrcidClient
from githuborg2rdf.config import Settings
from githuborg2rdf.metadata_quality import evaluate_metadata_quality
from githuborg2rdf.models import Contributor, DOIRecord, HarvestResult, Repository


class GitHubClientProtocol(Protocol):
    """Define the GitHub client methods required by the pipeline."""

    def list_repositories(self, organization: str) -> list[Repository]:
        """Return repositories belonging to an organization."""
        ...

    def list_contributors(
        self,
        repository: Repository,
    ) -> list[Contributor]:
        """Return contributors for a repository."""
        ...


def harvest_contributors(
    organization: str,
    client: GitHubClientProtocol,
) -> HarvestResult:
    """Harvest and merge contributors from all organization repositories."""
    contributors_by_login: dict[str, Contributor] = {}

    repositories = client.list_repositories(organization)
    enriched_repositories: list[Repository] = []

    for repository in repositories:
        repository_contributors = client.list_contributors(repository)

        enriched_repository = replace(
            repository,
            contributors=tuple(repository_contributors),
        )
        enriched_repositories.append(enriched_repository)

        for contributor in repository_contributors:
            existing = contributors_by_login.get(contributor.login)

            if existing is None:
                contributors_by_login[contributor.login] = replace(
                    contributor,
                    repositories=set(contributor.repositories),
                    contributions_by_repository=dict(
                        contributor.contributions_by_repository
                    ),
                )
                continue

            existing.repositories.update(contributor.repositories)
            existing.contributions += contributor.contributions
            existing.contributions_by_repository.update(
                contributor.contributions_by_repository
            )

    sorted_contributors = sorted(
        contributors_by_login.values(),
        key=lambda contributor: contributor.login.lower(),
    )

    return HarvestResult(
        organization=organization,
        repositories=enriched_repositories,
        contributors=sorted_contributors,
    )


def run_harvest(organization: str) -> HarvestResult:
    """Run the contributor harvest using application settings."""
    settings = Settings.from_environment()
    github_client = GitHubClient(settings)
    orcid_client = OrcidClient(
        access_token=settings.orcid_access_token,
    )
    datacite_client = DataCiteClient()

    result = harvest_contributors(organization, github_client)
    result = enrich_orcids(result, orcid_client)
    result = enrich_dois(result, datacite_client)
    evaluate_metadata_quality(result.doi_records)

    return result


def enrich_orcids(
    result: HarvestResult,
    client: ORCIDClient,
) -> HarvestResult:
    """Find ORCID identifiers for harvested contributors."""
    orcids_by_login: dict[str, str | None] = {}

    for contributor in result.contributors:
        login = contributor.login

        if login not in orcids_by_login:
            orcids_by_login[login] = client.find_orcid(login)

        contributor.orcid = orcids_by_login[login]

    return result


def enrich_dois(
    result: HarvestResult,
    client: DOIClient,
) -> HarvestResult:
    """Find DOI records for contributors with ORCIDs."""
    records_by_doi: dict[str, DOIRecord] = {}

    for contributor in result.contributors:
        if contributor.orcid is None:
            continue

        records = client.find_dois(contributor.orcid)

        for record in records:
            records_by_doi.setdefault(record.doi, record)
            contributor.doi_ids.add(record.doi)

    result.doi_records = sorted(
        records_by_doi.values(),
        key=lambda record: record.doi,
    )

    return result
