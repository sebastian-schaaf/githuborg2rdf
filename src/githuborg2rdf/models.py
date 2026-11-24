"""Data models used by the githuborg2rdf pipeline."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Repository:
    """Represent a GitHub repository."""

    owner: str
    name: str
    html_url: str
    contributors: tuple["Contributor", ...] = ()


@dataclass
class Contributor:
    """Represent a contributor to one or more GitHub repositories."""

    login: str
    html_url: str
    contributions: int
    repositories: set[str]
    contributions_by_repository: dict[str, int] = field(default_factory=dict)
    orcid: str | None = None
    doi_ids: set[str] = field(default_factory=set)
    is_bot: bool = False


@dataclass(frozen=True)
class NameIdentifier:
    """Represent an identifier assigned to a creator."""

    identifier: str
    scheme: str | None = None
    scheme_uri: str | None = None


@dataclass(frozen=True)
class Description:
    """Represent a DataCite description."""

    value: str
    description_type: str | None = None


@dataclass(frozen=True)
class RelatedIdentifier:
    """Represent a related resource identifier."""

    identifier: str
    identifier_type: str | None = None
    relation_type: str | None = None


@dataclass(frozen=True)
class FundingReference:
    """Represent a funding reference."""

    funder_name: str
    funder_identifier: str | None = None
    funder_identifier_type: str | None = None
    award_number: str | None = None
    award_title: str | None = None


@dataclass(frozen=True)
class Right:
    """Represent a license or other right."""

    rights: str | None = None
    rights_uri: str | None = None
    rights_identifier: str | None = None


@dataclass(frozen=True)
class DOIContributor:
    """Represent a person or organization from DOI metadata."""

    name: str
    orcid: str | None = None
    contributor_type: str | None = None
    name_identifiers: list[NameIdentifier] = field(
        default_factory=list,
    )


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
        """Return whether all five metadata checks passed."""
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


@dataclass
class DOIRecord:
    """Represent a DOI record retrieved from DataCite."""

    doi: str
    title: str | None = None
    resource_type: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    creators: list[DOIContributor] = field(default_factory=list)
    contributors: list[DOIContributor] = field(default_factory=list)
    rights_list: list[Right] = field(default_factory=list)
    descriptions: list[Description] = field(default_factory=list)
    related_identifiers: list[RelatedIdentifier] = field(
        default_factory=list,
    )
    funding_references: list[FundingReference] = field(
        default_factory=list,
    )
    metadata_quality: MetadataQualityResult | None = None


@dataclass
class HarvestResult:
    """Represent the complete result of an organization harvest."""

    organization: str
    repositories: list[Repository]
    contributors: list[Contributor]
    doi_records: list[DOIRecord] = field(default_factory=list)
