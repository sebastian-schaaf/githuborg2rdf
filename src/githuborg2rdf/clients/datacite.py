"""Client for retrieving DOI metadata from the DataCite REST API."""

from dataclasses import dataclass
from typing import Protocol

import requests

from githuborg2rdf.models import DOIContributor, DOIRecord


def _parse_doi_people(
    value: object,
    *,
    is_contributor: bool = False,
) -> list[DOIContributor]:
    """Parse creators or contributors from DataCite metadata."""
    if not isinstance(value, list):
        return []

    people: list[DOIContributor] = []

    for item in value:
        if not isinstance(item, dict):
            continue

        name = item.get("name")

        if not isinstance(name, str) or not name:
            continue

        orcid = _extract_orcid(item.get("nameIdentifiers"))

        contributor_type: str | None = None

        if is_contributor:
            raw_contributor_type = item.get("contributorType")

            if isinstance(raw_contributor_type, str):
                contributor_type = raw_contributor_type

        people.append(
            DOIContributor(
                name=name,
                orcid=orcid,
                contributor_type=contributor_type,
            )
        )

    return people


def _extract_title(value: object) -> str | None:
    """Extract the first title from DataCite metadata."""
    if not isinstance(value, list) or not value:
        return None

    first_title = value[0]

    if not isinstance(first_title, dict):
        return None

    title = first_title.get("title")

    if isinstance(title, str) and title:
        return title

    return None


def _extract_orcid(value: object) -> str | None:
    """Extract an ORCID from DataCite name identifiers."""
    if not isinstance(value, list):
        return None

    for item in value:
        if not isinstance(item, dict):
            continue

        scheme = item.get("nameIdentifierScheme")
        identifier = item.get("nameIdentifier")

        if scheme == "ORCID" and isinstance(identifier, str) and identifier:
            return identifier.removeprefix("https://orcid.org/").removeprefix(
                "http://orcid.org/"
            )

    return None


class DOIClient(Protocol):
    """Describe the interface required by the DOI enrichment step."""

    def find_dois(self, orcid: str) -> list[DOIRecord]:
        """Return DOI records associated with an ORCID."""


@dataclass
class DataCiteClient:
    """Retrieve DOI metadata associated with ORCID identifiers."""

    base_url: str = "https://api.datacite.org"

    def find_dois(self, orcid: str) -> list[DOIRecord]:
        """Return DOI records associated with an ORCID."""
        response = requests.get(
            f"{self.base_url}/dois",
            params={"query": f"orcid:{orcid}"},
            headers={"Accept": "application/vnd.api+json"},
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            return []

        raw_records = payload.get("data", [])

        if not isinstance(raw_records, list):
            return []

        records: list[DOIRecord] = []

        for item in raw_records:
            if not isinstance(item, dict):
                continue

            attributes = item.get("attributes")

            if not isinstance(attributes, dict):
                continue

            doi = attributes.get("doi")

            if not isinstance(doi, str) or not doi:
                continue

            title = _extract_title(attributes.get("titles"))

            raw_types = attributes.get("types")
            resource_type: str | None = None

            if isinstance(raw_types, dict):
                raw_resource_type = raw_types.get("resourceTypeGeneral")

                if isinstance(raw_resource_type, str):
                    resource_type = raw_resource_type

            publisher = attributes.get("publisher")

            if not isinstance(publisher, str):
                publisher = None

            publication_year = attributes.get("publicationYear")

            if not isinstance(publication_year, int):
                publication_year = None

            records.append(
                DOIRecord(
                    doi=doi,
                    title=title,
                    resource_type=resource_type,
                    publisher=publisher,
                    publication_year=publication_year,
                    creators=_parse_doi_people(attributes.get("creators")),
                    contributors=_parse_doi_people(
                        attributes.get("contributors"),
                        is_contributor=True,
                    ),
                )
            )

        return records
