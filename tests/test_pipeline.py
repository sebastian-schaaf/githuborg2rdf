"""Tests for the contributor harvesting pipeline."""

from typing import Any
from unittest.mock import MagicMock, patch

import requests

from githuborg2rdf.clients.orcid import OrcidClient
from githuborg2rdf.models import Contributor, DOIRecord, HarvestResult, Repository
from githuborg2rdf.pipeline import (
    enrich_dois,
    enrich_orcids,
    harvest_contributors,
    run_harvest,
)


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
    assert [repository.name for repository in result.repositories] == [
        "repo-one",
        "repo-two",
    ]

    assert [
        contributor.login for contributor in result.repositories[0].contributors
    ] == [
        "alice",
        "bob",
    ]

    assert [
        contributor.login for contributor in result.repositories[1].contributors
    ] == [
        "alice",
        "charlie",
    ]

    assert [
        contributor.contributions for contributor in result.repositories[0].contributors
    ] == [3, 1]

    assert [
        contributor.contributions for contributor in result.repositories[1].contributors
    ] == [5, 2]

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
    settings.orcid_access_token = "test-token"  # noqa: S105
    github_client = MagicMock()
    orcid_client = MagicMock()
    datacite_client = MagicMock()

    with (
        patch(
            "githuborg2rdf.pipeline.Settings.from_environment",
            return_value=settings,
        ) as mock_settings,
        patch(
            "githuborg2rdf.pipeline.GitHubClient",
            return_value=github_client,
        ) as mock_github_client,
        patch(
            "githuborg2rdf.pipeline.OrcidClient",
            return_value=orcid_client,
        ) as mock_orcid_client,
        patch(
            "githuborg2rdf.pipeline.DataCiteClient",
            return_value=datacite_client,
        ) as mock_datacite_client,
        patch(
            "githuborg2rdf.pipeline.harvest_contributors",
            return_value=expected,
        ) as mock_harvest,
        patch(
            "githuborg2rdf.pipeline.enrich_orcids",
            return_value=expected,
        ) as mock_enrich_orcids,
        patch(
            "githuborg2rdf.pipeline.enrich_dois",
            return_value=expected,
        ) as mock_enrich_dois,
        patch(
            "githuborg2rdf.pipeline.evaluate_metadata_quality",
        ) as mock_evaluate_metadata_quality,
    ):
        result = run_harvest("example")

    assert result == expected

    mock_settings.assert_called_once_with()
    mock_github_client.assert_called_once_with(settings)
    mock_orcid_client.assert_called_once()
    mock_datacite_client.assert_called_once_with()

    mock_harvest.assert_called_once_with(
        "example",
        github_client,
    )
    mock_enrich_orcids.assert_called_once_with(
        expected,
        orcid_client,
    )
    mock_orcid_client.assert_called_once_with(
        access_token="test-token",  # noqa: S106
    )
    mock_enrich_dois.assert_called_once_with(
        expected,
        datacite_client,
    )
    mock_evaluate_metadata_quality.assert_called_once_with(
        expected.doi_records,
    )


class FakeOrcidClient:
    """Return deterministic ORCID values for tests."""

    def __init__(self, results: dict[str, str | None]) -> None:
        """Initialize the fake client with configured ORCID results."""
        self.results = results
        self.calls: list[str] = []

    def find_orcid(self, contributor_name: str) -> str | None:
        """Return the configured ORCID for a contributor."""
        self.calls.append(contributor_name)
        return self.results.get(contributor_name)


class FakeResponse:
    """Represent a fake HTTP response."""

    def __init__(
        self,
        payload: object,
        status_code: int = 200,
    ) -> None:
        """Initialize the fake response."""
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise an HTTP error for unsuccessful responses."""
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP {self.status_code}",
            )

    def json(self) -> object:
        """Return the configured JSON payload."""
        return self.payload


def test_enrich_orcids_sets_matching_identifiers() -> None:
    """Set ORCIDs for matching contributors."""
    result = HarvestResult(
        organization="example",
        repositories=[],
        contributors=[
            Contributor(
                login="alice",
                html_url="https://github.com/alice",
                contributions=3,
                repositories={"repo-one"},
            ),
            Contributor(
                login="bob",
                html_url="https://github.com/bob",
                contributions=1,
                repositories={"repo-one"},
            ),
        ],
    )

    client = FakeOrcidClient(
        {
            "alice": "0000-0002-1825-0097",
            "bob": None,
        }
    )

    enriched_result = enrich_orcids(result, client)

    assert enriched_result is result
    assert result.contributors[0].orcid == "0000-0002-1825-0097"
    assert result.contributors[1].orcid is None
    assert client.calls == ["alice", "bob"]


def test_find_orcid_retries_without_invalid_access_token(
    monkeypatch: Any,
) -> None:
    """Retry without the token after an authentication failure."""
    responses = [
        FakeResponse(
            {"error": "invalid token"},
            status_code=401,
        ),
        FakeResponse(
            {
                "result": [
                    {
                        "orcid-identifier": {
                            "path": "0000-0002-1825-0097",
                        },
                    },
                ],
            }
        ),
    ]

    responses[0].status_code = 401
    responses[1].status_code = 200

    calls: list[dict[str, object]] = []

    def fake_get(
        url: str,
        *,
        params: dict[str, str],
        headers: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        calls.append(
            {
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return responses.pop(0)

    monkeypatch.setattr(
        "githuborg2rdf.clients.orcid.requests.get",
        fake_get,
    )

    client = OrcidClient(access_token="expired-token")  # noqa: S106

    assert client.find_orcid("Alice Example") == "0000-0002-1825-0097"
    assert len(calls) == 2
    assert calls[0]["headers"] == {
        "Accept": "application/json",
        "Authorization": "Bearer expired-token",
    }
    assert calls[1]["headers"] == {
        "Accept": "application/json",
    }


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


def test_run_harvest_evaluates_metadata_quality_after_doi_enrichment() -> None:
    """Evaluate metadata quality after DOI enrichment."""
    expected = HarvestResult(
        organization="example",
        repositories=[],
        contributors=[],
    )
    call_order: list[str] = []

    def fake_enrich_dois(
        result: HarvestResult,
        client: Any,
    ) -> HarvestResult:
        call_order.append("enrich_dois")
        return expected

    def fake_evaluate_metadata_quality(
        records: list[DOIRecord],
    ) -> None:
        call_order.append("evaluate_metadata_quality")
        assert records is expected.doi_records

    settings = MagicMock()
    settings.orcid_access_token = "test-token"  # noqa: S105

    with (
        patch(
            "githuborg2rdf.pipeline.Settings.from_environment",
            return_value=settings,
        ),
        patch("githuborg2rdf.pipeline.GitHubClient"),
        patch("githuborg2rdf.pipeline.OrcidClient"),
        patch("githuborg2rdf.pipeline.DataCiteClient"),
        patch(
            "githuborg2rdf.pipeline.harvest_contributors",
            return_value=expected,
        ),
        patch(
            "githuborg2rdf.pipeline.enrich_orcids",
            return_value=expected,
        ),
        patch(
            "githuborg2rdf.pipeline.enrich_dois",
            side_effect=fake_enrich_dois,
        ),
        patch(
            "githuborg2rdf.pipeline.evaluate_metadata_quality",
            side_effect=fake_evaluate_metadata_quality,
        ),
    ):
        run_harvest("example")

    assert call_order == [
        "enrich_dois",
        "evaluate_metadata_quality",
    ]
