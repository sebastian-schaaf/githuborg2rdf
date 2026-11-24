"""Client for retrieving DOI metadata from the DataCite REST API."""

from dataclasses import dataclass
from typing import Protocol

import requests

from githuborg2rdf.models import (
    Description,
    DOIContributor,
    DOIRecord,
    FundingReference,
    NameIdentifier,
    RelatedIdentifier,
    Right,
)


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

        name_identifiers = _parse_name_identifiers(
            item.get("nameIdentifiers"),
        )

        if is_contributor:
            raw_contributor_type = item.get("contributorType")

            if isinstance(raw_contributor_type, str):
                contributor_type = raw_contributor_type

        people.append(
            DOIContributor(
                name=name,
                orcid=orcid,
                contributor_type=contributor_type,
                name_identifiers=name_identifiers,
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
            params={"filter": f"orcid:{orcid}"},
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
                    rights_list=_parse_rights(attributes.get("rightsList")),
                    descriptions=_parse_descriptions(
                        attributes.get("descriptions"),
                    ),
                    related_identifiers=_parse_related_identifiers(
                        attributes.get("relatedIdentifiers"),
                    ),
                    funding_references=_parse_funding_references(
                        attributes.get("fundingReferences"),
                    ),
                )
            )

        return records


def _parse_name_identifiers(value: object) -> list[NameIdentifier]:
    """Parse DataCite name identifiers."""
    if not isinstance(value, list):
        return []

    identifiers: list[NameIdentifier] = []

    for item in value:
        if not isinstance(item, dict):
            continue

        identifier = item.get("nameIdentifier")

        if not isinstance(identifier, str) or not identifier:
            continue

        scheme = item.get("nameIdentifierScheme")
        if not isinstance(scheme, str):
            scheme = None

        scheme_uri = item.get("schemeUri")
        if not isinstance(scheme_uri, str):
            scheme_uri = None

        identifiers.append(
            NameIdentifier(
                identifier=identifier,
                scheme=scheme,
                scheme_uri=scheme_uri,
            )
        )

    return identifiers


def _parse_descriptions(value: object) -> list[Description]:
    """Parse DataCite descriptions."""
    if not isinstance(value, list):
        return []

    descriptions: list[Description] = []

    for item in value:
        if not isinstance(item, dict):
            continue

        description = item.get("description")

        if not isinstance(description, str):
            continue

        description_type = item.get("descriptionType")

        if not isinstance(description_type, str):
            description_type = None

        descriptions.append(
            Description(
                value=description,
                description_type=description_type,
            )
        )

    return descriptions


def _parse_rights(value: object) -> list[Right]:
    """Parse DataCite rights information."""
    if not isinstance(value, list):
        return []

    rights_list: list[Right] = []

    for item in value:
        if not isinstance(item, dict):
            continue

        rights = item.get("rights")
        rights_uri = item.get("rightsUri")
        rights_identifier = item.get("rightsIdentifier")

        rights_list.append(
            Right(
                rights=rights if isinstance(rights, str) else None,
                rights_uri=rights_uri if isinstance(rights_uri, str) else None,
                rights_identifier=(
                    rights_identifier if isinstance(rights_identifier, str) else None
                ),
            )
        )

    return rights_list


def _parse_related_identifiers(
    value: object,
) -> list[RelatedIdentifier]:
    """Parse DataCite related identifiers."""
    if not isinstance(value, list):
        return []

    identifiers: list[RelatedIdentifier] = []

    for item in value:
        if not isinstance(item, dict):
            continue

        identifier = item.get("relatedIdentifier")

        if not isinstance(identifier, str) or not identifier:
            continue

        identifier_type = item.get("relatedIdentifierType")
        relation_type = item.get("relationType")

        identifiers.append(
            RelatedIdentifier(
                identifier=identifier,
                identifier_type=(
                    identifier_type if isinstance(identifier_type, str) else None
                ),
                relation_type=(
                    relation_type if isinstance(relation_type, str) else None
                ),
            )
        )

    return identifiers


def _parse_funding_references(
    value: object,
) -> list[FundingReference]:
    """Parse DataCite funding references."""
    if not isinstance(value, list):
        return []

    references: list[FundingReference] = []

    for item in value:
        if not isinstance(item, dict):
            continue

        funder_name = item.get("funderName")

        if not isinstance(funder_name, str) or not funder_name:
            continue

        funder_identifier = item.get("funderIdentifier")
        funder_identifier_type = item.get("funderIdentifierType")
        award_number = item.get("awardNumber")
        award_title = item.get("awardTitle")

        references.append(
            FundingReference(
                funder_name=funder_name,
                funder_identifier=(
                    funder_identifier if isinstance(funder_identifier, str) else None
                ),
                funder_identifier_type=(
                    funder_identifier_type
                    if isinstance(funder_identifier_type, str)
                    else None
                ),
                award_number=(award_number if isinstance(award_number, str) else None),
                award_title=(award_title if isinstance(award_title, str) else None),
            )
        )

    return references
