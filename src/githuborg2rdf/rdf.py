"""Build RDF graphs from harvested GitHub organization data."""

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from githuborg2rdf.models import HarvestResult

SCHEMA = Namespace("https://schema.org/")
G2R = Namespace("https://github.com/sebastian-schaaf/githuborg2rdf/vocab/")


def build_graph(result: HarvestResult) -> Graph:
    """Build an RDF graph from a complete harvest result."""
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

        for repository_name, contribution_count in sorted(
            contributor.contributions_by_repository.items()
        ):
            contribution_repository_uri = repositories_by_name.get(repository_name)

            if contribution_repository_uri is None:
                continue

            contribution_uri = (
                BNode()
            )  # Blank node, as a single contribution does not require an external URI

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
                    Literal(contribution_count, datatype=XSD.integer),
                )
            )

    return graph
