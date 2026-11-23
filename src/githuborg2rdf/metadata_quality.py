"""Automated metadata quality checks for DOI records."""

from dataclasses import dataclass

from githuborg2rdf.models import DOIRecord

ORCID_SCHEME = "ORCID"
ORCID_SCHEME_URI = "https://orcid.org"


@dataclass(frozen=True)
class MetadataQualityResult:
    """Store the results of the five metadata quality checks."""

    has_license: bool
    has_description: bool
    creators_have_orcids: bool
    has_related_identifiers: bool
    has_funding: bool

    @property
    def passed(self) -> bool:
        """Return whether all five checks passed."""
        return all(
            (
                self.has_license,
                self.has_description,
                self.creators_have_orcids,
                self.has_related_identifiers,
                self.has_funding,
            )
        )

    def as_dict(self) -> dict[str, bool]:
        """Return the check results as a dictionary."""
        return {
            "license": self.has_license,
            "description": self.has_description,
            "creators_with_orcid": self.creators_have_orcids,
            "related_identifiers": self.has_related_identifiers,
            "funding": self.has_funding,
            "passed": self.passed,
        }


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
