"""Tests for RDF graph generation."""

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, XSD

from githuborg2rdf.models import Contributor, HarvestResult, Repository
from githuborg2rdf.rdf import G2R, SCHEMA, build_graph


def test_build_graph_exports_organization_repository_and_contribution() -> None:
    """Export organization, repository, contributor, and contribution data."""
    result = HarvestResult(
        organization="example",
        repositories=[
            Repository(
                owner="example",
                name="repo-one",
                html_url="https://github.com/example/repo-one",
            ),
        ],
        contributors=[
            Contributor(
                login="alice",
                html_url="https://github.com/alice",
                contributions=3,
                repositories={"repo-one"},
                contributions_by_repository={"repo-one": 3},
            ),
        ],
    )

    graph = build_graph(result)

    organization_uri = URIRef("https://github.com/example")
    repository_uri = URIRef("https://github.com/example/repo-one")
    contributor_uri = URIRef("https://github.com/alice")

    assert (
        organization_uri,
        RDF.type,
        SCHEMA.Organization,
    ) in graph

    assert (
        repository_uri,
        RDF.type,
        SCHEMA.SoftwareSourceCode,
    ) in graph

    assert (
        repository_uri,
        SCHEMA.isPartOf,
        organization_uri,
    ) in graph

    assert (
        contributor_uri,
        RDF.type,
        SCHEMA.Person,
    ) in graph

    contribution_nodes = list(graph.subjects(RDF.type, G2R.Contribution))

    assert len(contribution_nodes) == 1

    contribution_uri = contribution_nodes[0]

    assert (
        contribution_uri,
        G2R.contributor,
        contributor_uri,
    ) in graph

    assert (
        contribution_uri,
        G2R.repository,
        repository_uri,
    ) in graph

    assert (
        contribution_uri,
        G2R["count"],
        Literal(3, datatype=XSD.integer),
    ) in graph

    assert (
        contribution_uri,
        G2R["count"],
        next(literal for literal in graph.objects(contribution_uri, G2R["count"])),
    ) in graph

    count = next(graph.objects(contribution_uri, G2R["count"]))

    assert isinstance(count, Literal)
    assert count.toPython() == 3
    assert count.datatype == XSD.integer
