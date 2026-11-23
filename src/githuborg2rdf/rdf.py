"""Build RDF graphs from harvested GitHub organization data."""

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from githuborg2rdf.models import HarvestResult

SCHEMA = Namespace("https://schema.org/")
G2R = Namespace("https://github.com/sebastian-schaaf/githuborg2rdf/vocab/")


def _doi_uri(doi: str) -> URIRef:
    """Build a URI for a DOI."""
    return URIRef(f"https://doi.org/{doi}")


def _orcid_uri(orcid: str) -> URIRef:
    """Build a URI for an ORCID identifier."""
    return URIRef(f"https://orcid.org/{orcid}")


def build_graph(result: HarvestResult) -> Graph:
    """Build an RDF graph from a complete harvest result."""
    # build_graph()
    # ├── Init graph and namespaces
    # ├── Export organization
    # ├── Export repositories
    # ├── Export DOI datasets
    # │   ├── DOI metadata
    # │   ├── Creator
    # │   └── DataCite contributors
    # └── Export GitHub contributors
    #     ├── general contributor data
    #     ├── ORCID
    #     ├── DOI relations
    #     └── GitHub contributions

    graph = Graph()

    graph.bind("schema", SCHEMA)
    graph.bind("g2r", G2R)

    organization_uri = URIRef(f"https://github.com/{result.organization}")

    graph.add((organization_uri, RDF.type, SCHEMA.Organization))
    graph.add(
        (
            organization_uri,
            SCHEMA.name,
            Literal(result.organization),
        )
    )

    repositories_by_name: dict[str, URIRef] = {}

    for repository in result.repositories:
        repository_uri = URIRef(repository.html_url)
        repositories_by_name[repository.name] = repository_uri

        graph.add(
            (
                repository_uri,
                RDF.type,
                SCHEMA.SoftwareSourceCode,
            )
        )
        graph.add(
            (
                repository_uri,
                SCHEMA.name,
                Literal(repository.name),
            )
        )
        graph.add(
            (
                repository_uri,
                SCHEMA.url,
                repository_uri,
            )
        )
        graph.add(
            (
                repository_uri,
                SCHEMA.isPartOf,
                organization_uri,
            )
        )

    # Export DOI records and their metadata.
    for record in result.doi_records:
        record_uri = _doi_uri(record.doi)

        graph.add(
            (
                record_uri,
                RDF.type,
                SCHEMA.CreativeWork,
            )
        )

        if record.title is not None:
            graph.add(
                (
                    record_uri,
                    SCHEMA.name,
                    Literal(record.title),
                )
            )

        if record.resource_type is not None:
            graph.add(
                (
                    record_uri,
                    G2R.resourceType,
                    Literal(record.resource_type),
                )
            )

        if record.publisher is not None:
            graph.add(
                (
                    record_uri,
                    SCHEMA.publisher,
                    Literal(record.publisher),
                )
            )

        if record.publication_year is not None:
            graph.add(
                (
                    record_uri,
                    SCHEMA.datePublished,
                    Literal(
                        record.publication_year,
                        datatype=XSD.gYear,
                    ),
                )
            )

        for creator in record.creators:
            creator_node = BNode()

            graph.add(
                (
                    record_uri,
                    SCHEMA.creator,
                    creator_node,
                )
            )
            graph.add(
                (
                    creator_node,
                    RDF.type,
                    SCHEMA.Person,
                )
            )
            graph.add(
                (
                    creator_node,
                    SCHEMA.name,
                    Literal(creator.name),
                )
            )

            if creator.orcid:
                graph.add(
                    (
                        creator_node,
                        SCHEMA.identifier,
                        _orcid_uri(creator.orcid),
                    )
                )

        for doi_contributor in record.contributors:
            contributor_node = BNode()

            graph.add(
                (
                    record_uri,
                    SCHEMA.contributor,
                    contributor_node,
                )
            )
            graph.add(
                (
                    contributor_node,
                    RDF.type,
                    SCHEMA.Person,
                )
            )
            graph.add(
                (
                    contributor_node,
                    SCHEMA.name,
                    Literal(doi_contributor.name),
                )
            )

            if doi_contributor.contributor_type:
                graph.add(
                    (
                        contributor_node,
                        G2R.contributorType,
                        Literal(doi_contributor.contributor_type),
                    )
                )

            if doi_contributor.orcid:
                graph.add(
                    (
                        contributor_node,
                        SCHEMA.identifier,
                        _orcid_uri(doi_contributor.orcid),
                    )
                )

    for contributor in result.contributors:
        contributor_uri = URIRef(contributor.html_url)

        graph.add((contributor_uri, RDF.type, SCHEMA.Person))
        graph.add(
            (
                contributor_uri,
                SCHEMA.name,
                Literal(contributor.login),
            )
        )
        graph.add(
            (
                contributor_uri,
                SCHEMA.url,
                contributor_uri,
            )
        )
        graph.add(
            (
                contributor_uri,
                SCHEMA.memberOf,
                organization_uri,
            )
        )

        # Export the ORCID belonging to the GitHub contributor.
        if contributor.orcid:
            graph.add(
                (
                    contributor_uri,
                    SCHEMA.identifier,
                    _orcid_uri(contributor.orcid),
                )
            )

        # Link the GitHub contributor to their DOI records.
        for doi in sorted(contributor.doi_ids):
            graph.add(
                (
                    contributor_uri,
                    SCHEMA.citation,
                    _doi_uri(doi),
                )
            )

        for repository_name, contribution_count in sorted(
            contributor.contributions_by_repository.items()
        ):
            contribution_repository_uri = repositories_by_name.get(repository_name)

            if contribution_repository_uri is None:
                continue

            contribution_uri = BNode()

            graph.add(
                (
                    contribution_uri,
                    RDF.type,
                    G2R.Contribution,
                )
            )
            graph.add(
                (
                    contribution_uri,
                    G2R.contributor,
                    contributor_uri,
                )
            )
            graph.add(
                (
                    contribution_uri,
                    G2R.repository,
                    contribution_repository_uri,
                )
            )
            graph.add(
                (
                    contribution_uri,
                    G2R["count"],
                    Literal(
                        contribution_count,
                        datatype=XSD.integer,
                    ),
                )
            )

    return graph
