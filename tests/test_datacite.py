"""Tests for the DataCite client."""

from typing import Any

import pytest
import requests

from githuborg2rdf.clients.datacite import DataCiteClient
from githuborg2rdf.models import (
    DOIContributor,
    NameIdentifier,
)


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


def test_find_dois_parses_doi_metadata(
    monkeypatch: Any,
) -> None:
    """Parse DOI metadata including creators and contributors."""
    payload = {
        "data": [
            {
                "attributes": {
                    "doi": "10.5281/example.123",
                    "titles": [
                        {
                            "title": "Example software",
                        },
                    ],
                    "types": {
                        "resourceTypeGeneral": "Software",
                    },
                    "publisher": "Zenodo",
                    "publicationYear": 2025,
                    "rightsList": [
                        {
                            "rights": "Creative Commons Attribution 4.0",
                            "rightsUri": "https://creativecommons.org/licenses/by/4.0/",
                            "rightsIdentifier": "CC-BY-4.0",
                        },
                    ],
                    "descriptions": [
                        {
                            "description": (
                                "This is a sufficiently long description containing more "
                                "than one hundred characters so that the metadata quality "
                                "check can pass for this record."
                            ),
                            "descriptionType": "Abstract",
                        },
                    ],
                    "relatedIdentifiers": [
                        {
                            "relatedIdentifier": "https://github.com/example/repository",
                            "relatedIdentifierType": "URL",
                            "relationType": "IsSupplementTo",
                        },
                    ],
                    "fundingReferences": [
                        {
                            "funderName": "Example Research Foundation",
                            "funderIdentifier": "https://ror.org/012345678",
                            "funderIdentifierType": "ROR",
                            "awardNumber": "EXAMPLE-2025-001",
                            "awardTitle": "Example Research Grant",
                        },
                    ],
                    "creators": [
                        {
                            "name": "Alice Example",
                            "nameIdentifiers": [
                                {
                                    "nameIdentifier": (
                                        "https://orcid.org/0000-0002-1825-0097"
                                    ),
                                    "nameIdentifierScheme": "ORCID",
                                },
                            ],
                        },
                    ],
                    "contributors": [
                        {
                            "name": "Bob Example",
                            "contributorType": "DataCurator",
                        },
                    ],
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
        assert url == "https://api.datacite.org/dois"
        assert params == {"query": "orcid:0000-0002-1825-0097"}
        assert headers == {
            "Accept": "application/vnd.api+json",
        }
        assert timeout == 30

        return FakeResponse(payload)

    monkeypatch.setattr(
        "githuborg2rdf.clients.datacite.requests.get",
        fake_get,
    )

    client = DataCiteClient()
    records = client.find_dois("0000-0002-1825-0097")

    assert len(records) == 1

    record = records[0]

    assert record.doi == "10.5281/example.123"
    assert record.title == "Example software"
    assert record.resource_type == "Software"
    assert record.publisher == "Zenodo"
    assert record.publication_year == 2025

    assert record.creators == [
        DOIContributor(
            name="Alice Example",
            orcid="0000-0002-1825-0097",
            name_identifiers=[
                NameIdentifier(
                    identifier="https://orcid.org/0000-0002-1825-0097",
                    scheme="ORCID",
                ),
            ],
        ),
    ]

    assert record.contributors == [
        DOIContributor(
            name="Bob Example",
            contributor_type="DataCurator",
        ),
    ]

    assert len(record.rights_list) == 1
    assert record.rights_list[0].rights == "Creative Commons Attribution 4.0"
    assert (
        record.rights_list[0].rights_uri
        == "https://creativecommons.org/licenses/by/4.0/"
    )
    assert record.rights_list[0].rights_identifier == "CC-BY-4.0"

    assert len(record.descriptions) == 1
    assert record.descriptions[0].description_type == "Abstract"
    assert len(record.descriptions[0].value) >= 100

    assert len(record.related_identifiers) == 1
    assert (
        record.related_identifiers[0].identifier
        == "https://github.com/example/repository"
    )
    assert record.related_identifiers[0].identifier_type == "URL"
    assert record.related_identifiers[0].relation_type == "IsSupplementTo"

    assert len(record.funding_references) == 1
    assert record.funding_references[0].funder_name == "Example Research Foundation"
    assert record.funding_references[0].funder_identifier == "https://ror.org/012345678"
    assert record.funding_references[0].funder_identifier_type == "ROR"
    assert record.funding_references[0].award_number == "EXAMPLE-2025-001"
    assert record.funding_references[0].award_title == "Example Research Grant"


def test_find_dois_returns_empty_list_without_matches(
    monkeypatch: Any,
) -> None:
    """Return no records when DataCite finds no DOI."""
    payload: dict[str, Any] = {
        "data": [],
    }

    monkeypatch.setattr(
        "githuborg2rdf.clients.datacite.requests.get",
        lambda *args, **kwargs: FakeResponse(payload),
    )

    client = DataCiteClient()

    assert client.find_dois("0000-0002-1825-0097") == []


def test_find_dois_normalizes_orcid_url(
    monkeypatch: Any,
) -> None:
    """Normalize an ORCID URL to the bare ORCID identifier."""
    payload = {
        "data": [
            {
                "attributes": {
                    "doi": "10.5281/example.456",
                    "creators": [
                        {
                            "name": "Alice Example",
                            "nameIdentifiers": [
                                {
                                    "nameIdentifier": (
                                        "https://orcid.org/0000-0002-1825-0097"
                                    ),
                                    "nameIdentifierScheme": "ORCID",
                                },
                            ],
                        },
                    ],
                },
            },
        ],
    }

    monkeypatch.setattr(
        "githuborg2rdf.clients.datacite.requests.get",
        lambda *args, **kwargs: FakeResponse(payload),
    )

    client = DataCiteClient()
    records = client.find_dois("0000-0002-1825-0097")

    assert records[0].creators[0].orcid == ("0000-0002-1825-0097")


def test_find_dois_propagates_http_errors(
    monkeypatch: Any,
) -> None:
    """Propagate HTTP errors from DataCite."""

    def fake_get(*args: Any, **kwargs: Any) -> requests.Response:
        response = requests.Response()
        response.status_code = 500
        response.url = "https://api.datacite.org/dois"
        return response

    monkeypatch.setattr(
        "githuborg2rdf.clients.datacite.requests.get",
        fake_get,
    )

    client = DataCiteClient()

    with pytest.raises(requests.HTTPError):
        client.find_dois("0000-0002-1825-0097")
