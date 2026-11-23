"""Automated metadata quality checks for DOI records."""

from githuborg2rdf.models import (
    DOIRecord,
    MetadataQualityResult,
)

ORCID_SCHEME = "ORCID"
ORCID_SCHEME_URI = "https://orcid.org"


def _has_license(record: DOIRecord) -> bool:
    """Return whether the record contains at least one licence."""
    return bool(record.rights_list)


def _has_description(record: DOIRecord) -> bool:
    """Return whether one description contains at least 100 characters."""
    return any(len(description.value) >= 100 for description in record.descriptions)


def _creator_has_orcid(creator: object) -> bool:
    """Return whether one creator has an ORCID identifier."""
    name_identifiers = getattr(creator, "name_identifiers", [])

    for identifier in name_identifiers:
        if (
            identifier.scheme == ORCID_SCHEME
            or identifier.scheme_uri == ORCID_SCHEME_URI
        ):
            return True

    # DOIContributor already stores the extracted ORCID separately.
    orcid = getattr(creator, "orcid", None)

    return isinstance(orcid, str) and bool(orcid)


def _creators_have_orcids(record: DOIRecord) -> bool:
    """Return whether every creator has an ORCID."""
    if not record.creators:
        return False

    return all(_creator_has_orcid(creator) for creator in record.creators)


def _has_related_identifiers(record: DOIRecord) -> bool:
    """Return whether the record has a related resource."""
    return bool(record.related_identifiers)


def _has_funding(record: DOIRecord) -> bool:
    """Return whether the record names at least one funder."""
    return bool(record.funding_references)


def check_metadata_quality(record: DOIRecord) -> MetadataQualityResult:
    """Run all five metadata quality checks for one DOI record."""
    return MetadataQualityResult(
        has_license=_has_license(record),
        has_description=_has_description(record),
        creators_have_orcids=_creators_have_orcids(record),
        has_related_identifiers=_has_related_identifiers(record),
        has_funding=_has_funding(record),
    )


def evaluate_metadata_quality(
    records: list[DOIRecord],
) -> None:
    """Attach metadata quality results to DOI records."""
    for record in records:
        record.metadata_quality = check_metadata_quality(record)
