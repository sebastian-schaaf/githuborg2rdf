"""Tests for the contributor harvesting pipeline."""

from githuborg2rdf.models import Contributor, Repository
from githuborg2rdf.pipeline import harvest_contributors


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
                ),
                Contributor(
                    login="bob",
                    html_url="https://github.com/bob",
                    contributions=1,
                    repositories={"repo-one"},
                ),
            ]

        return [
            Contributor(
                login="alice",
                html_url="https://github.com/alice",
                contributions=5,
                repositories={"repo-two"},
            ),
            Contributor(
                login="charlie",
                html_url="https://github.com/charlie",
                contributions=2,
                repositories={"repo-two"},
            ),
        ]


def test_harvest_contributors_merges_and_sorts() -> None:
    """Merge contributors across repositories and sort by login."""
    contributors = harvest_contributors("example", FakeGitHubClient())

    assert [contributor.login for contributor in contributors] == [
        "alice",
        "bob",
        "charlie",
    ]

    alice = contributors[0]
    assert alice.contributions == 8
    assert alice.repositories == {"repo-one", "repo-two"}

    bob = contributors[1]
    assert bob.contributions == 1
    assert bob.repositories == {"repo-one"}

    charlie = contributors[2]
    assert charlie.contributions == 2
    assert charlie.repositories == {"repo-two"}


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

    assert harvest_contributors("empty-example", EmptyGitHubClient()) == []
