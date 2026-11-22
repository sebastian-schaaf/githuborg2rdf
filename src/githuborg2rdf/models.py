"""Data models used by the githuborg2rdf pipeline."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Repository:
    """Represent a GitHub repository."""

    owner: str
    name: str
    html_url: str


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
class DOIContributor:
    """Represent a person or organization from DOI metadata."""

    name: str
    orcid: str | None = None
    contributor_type: str | None = None


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


@dataclass
class HarvestResult:
    """Represent the complete result of an organization harvest."""

    organization: str
    repositories: list[Repository]
    contributors: list[Contributor]
    doi_records: list[DOIRecord] = field(default_factory=list)
