"""Tests for DOI metadata quality checks."""

from githuborg2rdf.metadata_quality import check_metadata_quality
from githuborg2rdf.models import (
    Description,
    DOIContributor,
    DOIRecord,
    FundingReference,
    NameIdentifier,
    RelatedIdentifier,
    Right,
)


def _long_description(length: int = 100) -> str:
    """Return a description with the requested length."""
    return "x" * length


def _complete_record() -> DOIRecord:
    """Return a DOI record passing all five quality checks."""
    return DOIRecord(
        doi="10.5281/example.123",
        creators=[
            DOIContributor(
                name="Alice Example",
                orcid="0000-0002-1825-0097",
                name_identifiers=[
                    NameIdentifier(
                        identifier=("https://orcid.org/0000-0002-1825-0097"),
                        scheme="ORCID",
                    ),
                ],
            ),
        ],
        rights_list=[
            Right(
                rights="Creative Commons Attribution 4.0",
                rights_uri=("https://creativecommons.org/licenses/by/4.0/"),
                rights_identifier="CC-BY-4.0",
            ),
        ],
        descriptions=[
            Description(
                value=_long_description(),
                description_type="Abstract",
            ),
        ],
        related_identifiers=[
            RelatedIdentifier(
                identifier="https://github.com/example/repository",
                identifier_type="URL",
                relation_type="IsSupplementTo",
            ),
        ],
        funding_references=[
            FundingReference(
                funder_name="Example Research Foundation",
                funder_identifier="https://ror.org/012345678",
                funder_identifier_type="ROR",
                award_number="EXAMPLE-2025-001",
                award_title="Example Research Grant",
            ),
        ],
    )


def test_complete_record_passes_all_checks() -> None:
    """A complete record passes all five quality checks."""
    result = check_metadata_quality(_complete_record())

    assert result.has_license is True
    assert result.has_description is True
    assert result.creators_have_orcids is True
    assert result.has_related_identifiers is True
    assert result.has_funding is True
    assert result.passed is True


def test_license_check_fails_without_rights() -> None:
    """The licence check fails when rightsList is empty."""
    record = _complete_record()
    record.rights_list = []

    result = check_metadata_quality(record)

    assert result.has_license is False
    assert result.passed is False


def test_description_check_fails_below_100_characters() -> None:
    """The description check fails for descriptions shorter than 100."""
    record = _complete_record()
    record.descriptions = [
        Description(
            value=_long_description(99),
            description_type="Abstract",
        ),
    ]

    result = check_metadata_quality(record)

    assert result.has_description is False


def test_description_check_passes_at_exactly_100_characters() -> None:
    """The description check passes for exactly 100 characters."""
    record = _complete_record()
    record.descriptions = [
        Description(
            value=_long_description(100),
            description_type="Abstract",
        ),
    ]

    result = check_metadata_quality(record)

    assert result.has_description is True


def test_description_check_passes_if_one_description_is_long_enough() -> None:
    """One sufficiently long description is enough."""
    record = _complete_record()
    record.descriptions = [
        Description(value=_long_description(50)),
        Description(value=_long_description(100)),
    ]

    result = check_metadata_quality(record)

    assert result.has_description is True


def test_creator_check_fails_without_creators() -> None:
    """The creator check fails when no creator is listed."""
    record = _complete_record()
    record.creators = []

    result = check_metadata_quality(record)

    assert result.creators_have_orcids is False


def test_creator_check_fails_if_one_creator_has_no_orcid() -> None:
    """Every creator must have an ORCID."""
    record = _complete_record()
    record.creators = [
        DOIContributor(
            name="Alice Example",
            orcid="0000-0002-1825-0097",
        ),
        DOIContributor(
            name="Bob Example",
        ),
    ]

    result = check_metadata_quality(record)

    assert result.creators_have_orcids is False


def test_creator_check_passes_for_multiple_creators_with_orcids() -> None:
    """The creator check passes when every creator has an ORCID."""
    record = _complete_record()
    record.creators = [
        DOIContributor(
            name="Alice Example",
            orcid="0000-0002-1825-0097",
        ),
        DOIContributor(
            name="Bob Example",
            orcid="0000-0003-1234-5678",
        ),
    ]

    result = check_metadata_quality(record)

    assert result.creators_have_orcids is True


def test_creator_check_accepts_orcid_from_name_identifiers() -> None:
    """An ORCID in nameIdentifiers is sufficient."""
    record = _complete_record()
    record.creators = [
        DOIContributor(
            name="Alice Example",
            name_identifiers=[
                NameIdentifier(
                    identifier="0000-0002-1825-0097",
                    scheme="ORCID",
                ),
            ],
        ),
    ]

    result = check_metadata_quality(record)

    assert result.creators_have_orcids is True


def test_related_identifier_check_fails_without_related_resources() -> None:
    """The related identifier check fails for an empty list."""
    record = _complete_record()
    record.related_identifiers = []

    result = check_metadata_quality(record)

    assert result.has_related_identifiers is False


def test_funding_check_fails_without_funding_references() -> None:
    """The funding check fails when no funder is listed."""
    record = _complete_record()
    record.funding_references = []

    result = check_metadata_quality(record)

    assert result.has_funding is False


def test_as_dict_contains_all_check_results() -> None:
    """The result can be exported as a dictionary."""
    result = check_metadata_quality(_complete_record())

    assert result.as_dict() == {
        "license": True,
        "description": True,
        "creators_with_orcid": True,
        "related_identifiers": True,
        "funding": True,
        "passed": True,
    }
