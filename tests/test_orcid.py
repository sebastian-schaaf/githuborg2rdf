"""Tests for the ORCID client."""

from typing import Any

import pytest
import requests

from githuborg2rdf.clients.orcid import OrcidClient


class FakeResponse:
    """Represent a minimal successful HTTP response."""

    def __init__(self, payload: object) -> None:
        """Initialize the response with a JSON-compatible payload."""
        self.payload = payload

    def raise_for_status(self) -> None:
        """Do not raise for successful fake responses."""

    def json(self) -> object:
        """Return the configured JSON payload."""
        return self.payload


def test_find_orcid_returns_first_match(
    monkeypatch: Any,
) -> None:
    """Return the first ORCID search result."""
    payload = {
        "result": [
            {
                "orcid-identifier": {
                    "path": "0000-0002-1825-0097",
                },
            },
            {
                "orcid-identifier": {
                    "path": "0000-0003-1234-5678",
                },
            },
        ],
    }

    def fake_get(
        url: str,
        *,
        params: dict[str, str],
        headers: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        assert url == "https://pub.orcid.org/v3.0/search"
        assert params == {
            "q": 'credit-name:"Alice Example"',
        }
        assert headers == {
            "Accept": "application/json",
        }
        assert timeout == 30

        return FakeResponse(payload)

    monkeypatch.setattr(
        "githuborg2rdf.clients.orcid.requests.get",
        fake_get,
    )

    client = OrcidClient()

    assert client.find_orcid("Alice Example") == "0000-0002-1825-0097"


def test_find_orcid_returns_none_without_match(
    monkeypatch: Any,
) -> None:
    """Return None when the ORCID search has no results."""
    payload: dict[str, object] = {
        "result": [],
    }

    monkeypatch.setattr(
        "githuborg2rdf.clients.orcid.requests.get",
        lambda *args, **kwargs: FakeResponse(payload),
    )

    client = OrcidClient()

    assert client.find_orcid("Unknown Contributor") is None


def test_find_orcid_returns_none_for_empty_name() -> None:
    """Do not perform a request for an empty contributor name."""
    client = OrcidClient()

    assert client.find_orcid("") is None
    assert client.find_orcid("   ") is None


def test_find_orcid_supports_access_token(
    monkeypatch: Any,
) -> None:
    """Include a bearer token when one is configured."""
    payload = {
        "result": [
            {
                "orcid-identifier": {
                    "path": "0000-0002-1825-0097",
                },
            },
        ],
    }

    def fake_get(
        url: str,
        *,
        params: dict[str, str],
        headers: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        assert headers == {
            "Accept": "application/json",
            "Authorization": "Bearer test-token",
        }
        return FakeResponse(payload)

    monkeypatch.setattr(
        "githuborg2rdf.clients.orcid.requests.get",
        fake_get,
    )

    client = OrcidClient(access_token="test-token")  # noqa: S106

    assert client.find_orcid("Alice Example") == "0000-0002-1825-0097"


def test_find_orcid_propagates_http_errors(
    monkeypatch: Any,
) -> None:
    """Propagate HTTP errors from the ORCID API."""

    def fake_get(*args: Any, **kwargs: Any) -> requests.Response:
        response = requests.Response()
        response.status_code = 500
        response.url = "https://pub.orcid.org/v3.0/search"
        return response

    monkeypatch.setattr(
        "githuborg2rdf.clients.orcid.requests.get",
        fake_get,
    )

    client = OrcidClient()

    with pytest.raises(requests.HTTPError):
        client.find_orcid("Alice Example")


def test_find_orcid_handles_invalid_payload(
    monkeypatch: Any,
) -> None:
    """Return None for an unexpected response structure."""
    monkeypatch.setattr(
        "githuborg2rdf.clients.orcid.requests.get",
        lambda *args, **kwargs: FakeResponse(
            {"unexpected": "payload"},
        ),
    )

    client = OrcidClient()

    assert client.find_orcid("Alice Example") is None
