"""Tests for the GitHub API client."""

from unittest.mock import MagicMock, patch

import pytest

from githuborg2rdf.clients.github import GitHubApiError, GitHubClient
from githuborg2rdf.config import Settings
from githuborg2rdf.models import Repository


def create_client() -> GitHubClient:
    """Create a GitHub client with mocked settings."""
    settings = MagicMock(spec=Settings)
    settings.github_api_url = "https://api.github.com"
    settings.github_token = None
    return GitHubClient(settings)


def create_response(
    payload: object,
    *,
    status_code: int = 200,
    ok: bool = True,
) -> MagicMock:
    """Create a mocked HTTP response."""
    response = MagicMock()
    response.ok = ok
    response.status_code = status_code
    response.url = "https://api.github.com/test"
    response.text = str(payload)
    response.json.return_value = payload
    return response


def test_get_paginated_requests_all_pages() -> None:
    """Fetch all pages until an empty page is returned."""
    client = create_client()

    with patch.object(
        client.session,
        "get",
        side_effect=[
            create_response([{"id": 1}, {"id": 2}]),
            create_response([{"id": 3}]),
            create_response([]),
        ],
    ) as mock_get:
        result = list(client._get_paginated("/test"))

    assert result == [{"id": 1}, {"id": 2}, {"id": 3}]
    assert mock_get.call_count == 3

    calls = mock_get.call_args_list
    assert calls[0].kwargs["params"] == {"per_page": 100, "page": 1}
    assert calls[1].kwargs["params"] == {"per_page": 100, "page": 2}
    assert calls[2].kwargs["params"] == {"per_page": 100, "page": 3}


def test_list_repositories() -> None:
    """Convert GitHub repository responses to Repository instances."""
    client = create_client()

    with patch.object(
        client.session,
        "get",
        side_effect=[
            create_response(
                [
                    {
                        "name": "repo-one",
                        "html_url": "https://github.com/example/repo-one",
                    }
                ]
            ),
            create_response([]),
        ],
    ) as mock_get:
        repositories = client.list_repositories("example")

    assert repositories == [
        Repository(
            owner="example",
            name="repo-one",
            html_url="https://github.com/example/repo-one",
        )
    ]
    assert mock_get.call_count == 2


def test_list_contributors_filters_bots() -> None:
    """Exclude contributors identified as bots."""
    client = create_client()

    repository = Repository(
        owner="example",
        name="repo-one",
        html_url="https://github.com/example/repo-one",
    )

    with patch.object(
        client.session,
        "get",
        side_effect=[
            create_response(
                [
                    {
                        "login": "alice",
                        "type": "User",
                        "html_url": "https://github.com/alice",
                        "contributions": 5,
                    },
                    {
                        "login": "dependabot[bot]",
                        "type": "Bot",
                        "html_url": "https://github.com/dependabot",
                        "contributions": 10,
                    },
                    {
                        "login": "renovate[bot]",
                        "type": "User",
                        "html_url": "https://github.com/renovate",
                        "contributions": 8,
                    },
                ]
            ),
            create_response([]),
        ],
    ) as mock_get:
        contributors = client.list_contributors(repository)

    assert len(contributors) == 1
    assert contributors[0].login == "alice"
    assert contributors[0].html_url == "https://github.com/alice"
    assert contributors[0].contributions == 5
    assert contributors[0].repositories == {"repo-one"}
    assert mock_get.call_count == 2


def test_get_paginated_raises_for_http_error() -> None:
    """Raise GitHubApiError for unsuccessful HTTP responses."""
    client = create_client()

    with patch.object(
        client.session,
        "get",
        return_value=create_response(
            {"message": "Forbidden"},
            status_code=403,
            ok=False,
        ),
    ) as mock_get:
        with pytest.raises(GitHubApiError, match="403"):
            list(client._get_paginated("/test"))

    mock_get.assert_called_once()


def test_get_paginated_raises_for_non_list_response() -> None:
    """Raise GitHubApiError when the API response is not a list."""
    client = create_client()

    with patch.object(
        client.session,
        "get",
        return_value=create_response({"message": "Not found"}),
    ) as mock_get:
        with pytest.raises(GitHubApiError, match="Expected a list"):
            list(client._get_paginated("/test"))

    mock_get.assert_called_once()
