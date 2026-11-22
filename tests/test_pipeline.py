"""Tests for the contributor harvesting pipeline."""

from unittest.mock import MagicMock, patch

from githuborg2rdf.models import Contributor, DOIRecord, HarvestResult, Repository
from githuborg2rdf.pipeline import enrich_dois, harvest_contributors, run_harvest


class FakeGitHubClient:
    """Fake GitHub client for pipeline tests."""

    def list_repositories(self, organization: str) -> list[Repository]:
        """Return repositories for the test organization."""
        assert organization == "example"

        return [
            Repository(
                owner="example",
                name="repo-one",
                html_url="https://github.com/example/repo-one",
            ),
            Repository(
                owner="example",
                name="repo-two",
                html_url="https://github.com/example/repo-two",
            ),
        ]

    def list_contributors(
        self,
        repository: Repository,
    ) -> list[Contributor]:
        """Return contributors for the requested repository."""
        if repository.name == "repo-one":
            return [
                Contributor(
                    login="alice",
                    html_url="https://github.com/alice",
                    contributions=3,
                    repositories={"repo-one"},
                    contributions_by_repository={
                        "repo-one": 3,
                    },
                ),
                Contributor(
                    login="bob",
                    html_url="https://github.com/bob",
                    contributions=1,
                    repositories={"repo-one"},
                    contributions_by_repository={
                        "repo-one": 1,
                    },
                ),
            ]

        return [
            Contributor(
                login="alice",
                html_url="https://github.com/alice",
                contributions=5,
                repositories={"repo-two"},
                contributions_by_repository={
                    "repo-two": 5,
                },
            ),
            Contributor(
                login="charlie",
                html_url="https://github.com/charlie",
                contributions=2,
                repositories={"repo-two"},
                contributions_by_repository={
                    "repo-two": 2,
                },
            ),
        ]


def test_harvest_contributors_merges_and_sorts() -> None:
    """Merge contributors across repositories and sort by login."""
    result = harvest_contributors("example", FakeGitHubClient())
    contributors = result.contributors

    assert result.organization == "example"
    assert result.repositories == [
        Repository(
            owner="example",
            name="repo-one",
            html_url="https://github.com/example/repo-one",
        ),
        Repository(
            owner="example",
            name="repo-two",
            html_url="https://github.com/example/repo-two",
        ),
    ]

    assert [contributor.login for contributor in contributors] == [
        "alice",
        "bob",
        "charlie",
    ]

    alice = contributors[0]
    assert alice.contributions == 8
    assert alice.repositories == {"repo-one", "repo-two"}
    assert alice.contributions_by_repository == {
        "repo-one": 3,
        "repo-two": 5,
    }

    bob = contributors[1]
    assert bob.contributions == 1
    assert bob.repositories == {"repo-one"}
    assert bob.contributions_by_repository == {
        "repo-one": 1,
    }

    charlie = contributors[2]
    assert charlie.contributions == 2
    assert charlie.repositories == {"repo-two"}
    assert charlie.contributions_by_repository == {
        "repo-two": 2,
    }


def test_harvest_contributors_returns_empty_result() -> None:
    """Return an empty list when the organization has no repositories."""

    class EmptyGitHubClient:
        """Fake client without repositories."""

        def list_repositories(self, organization: str) -> list[Repository]:
            """Return no repositories."""
            return []

        def list_contributors(
            self,
            repository: Repository,
        ) -> list[Contributor]:
            """Return no contributors."""
            return []

    result = harvest_contributors("empty-example", EmptyGitHubClient())

    assert result.organization == "empty-example"
    assert result.repositories == []
    assert result.contributors == []


def test_run_harvest_creates_client_and_delegates() -> None:
    """Create a configured client and delegate harvesting."""
    expected = HarvestResult(
        organization="example",
        repositories=[
            Repository(
                owner="example",
                name="repo-one",
                html_url="https://github.com/example/repo-one",
            )
        ],
        contributors=[
            Contributor(
                login="alice",
                html_url="https://github.com/alice",
                contributions=3,
                repositories={"repo-one"},
            )
        ],
    )

    settings = MagicMock()
    client = MagicMock()

    with (
        patch(
            "githuborg2rdf.pipeline.Settings.from_environment",
            return_value=settings,
        ) as mock_settings,
        patch(
            "githuborg2rdf.pipeline.GitHubClient",
            return_value=client,
        ) as mock_client_class,
        patch(
            "githuborg2rdf.pipeline.harvest_contributors",
            return_value=expected,
        ) as mock_harvest,
    ):
        result = run_harvest("example")

    assert result == expected
    mock_settings.assert_called_once_with()
    mock_client_class.assert_called_once_with(settings)
    mock_harvest.assert_called_once_with("example", client)


class FakeDataCiteClient:
    """Return deterministic DOI records for tests."""

    def find_dois(self, orcid: str) -> list[DOIRecord]:
        """Return DOI records associated with an ORCID."""
        if orcid in {
            "0000-0002-1825-0097",
            "0000-0003-1234-5678",
        }:
            return [
                DOIRecord(
                    doi="10.5281/zenodo.1234567",
                    title="Example software",
                    resource_type="Software",
                    publisher="Zenodo",
                    publication_year=2025,
                )
            ]

        return []


def test_enrich_dois_deduplicates_shared_records() -> None:
    """Associate one shared DOI with multiple contributors."""
    result = HarvestResult(
        organization="example",
        repositories=[],
        contributors=[
            Contributor(
                login="alice",
                html_url="https://github.com/alice",
                contributions=3,
                repositories={"repo-one"},
                orcid="0000-0002-1825-0097",
            ),
            Contributor(
                login="bob",
                html_url="https://github.com/bob",
                contributions=1,
                repositories={"repo-one"},
                orcid="0000-0003-1234-5678",
            ),
        ],
    )

    enriched_result = enrich_dois(result, FakeDataCiteClient())

    assert len(enriched_result.doi_records) == 1
    assert enriched_result.doi_records[0].doi == ("10.5281/zenodo.1234567")

    assert result.contributors[0].doi_ids == {
        "10.5281/zenodo.1234567",
    }
    assert result.contributors[1].doi_ids == {
        "10.5281/zenodo.1234567",
    }
