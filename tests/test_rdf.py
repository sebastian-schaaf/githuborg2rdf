"""Tests for RDF graph generation."""

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from githuborg2rdf.metadata_quality import check_metadata_quality
from githuborg2rdf.models import (
    Contributor,
    DOIContributor,
    DOIRecord,
    HarvestResult,
    Repository,
)
from githuborg2rdf.rdf import (
    DQV,
    G2R,
    QUALITY,
    SCHEMA,
    add_metadata_quality_measurements,
    build_graph,
)


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


def test_build_graph_exports_contributor_orcid_and_doi() -> None:
    """Export a contributor's ORCID and DOI reference."""
    result = HarvestResult(
        organization="example",
        repositories=[],
        contributors=[
            Contributor(
                login="alice",
                html_url="https://github.com/alice",
                contributions=3,
                repositories=set(),
                contributions_by_repository={},
                orcid="0000-0002-1825-0097",
                doi_ids={"10.5281/example.123"},
            ),
        ],
        doi_records=[
            DOIRecord(
                doi="10.5281/example.123",
                title="Example software",
                resource_type="Software",
                publisher="Zenodo",
                publication_year=2025,
            ),
        ],
    )

    graph = build_graph(result)

    contributor_uri = URIRef("https://github.com/alice")
    orcid_uri = URIRef("https://orcid.org/0000-0002-1825-0097")
    doi_uri = URIRef("https://doi.org/10.5281/example.123")

    assert (
        contributor_uri,
        SCHEMA.identifier,
        orcid_uri,
    ) in graph

    assert (
        contributor_uri,
        SCHEMA.citation,
        doi_uri,
    ) in graph

    assert (
        doi_uri,
        RDF.type,
        SCHEMA.CreativeWork,
    ) in graph


def test_build_graph_exports_doi_metadata() -> None:
    """Export metadata for a DOI record."""
    result = HarvestResult(
        organization="example",
        repositories=[],
        contributors=[],
        doi_records=[
            DOIRecord(
                doi="10.5281/example.456",
                title="Example dataset",
                resource_type="Dataset",
                publisher="Example Publisher",
                publication_year=2024,
            ),
        ],
    )

    graph = build_graph(result)

    doi_uri = URIRef("https://doi.org/10.5281/example.456")

    assert (
        doi_uri,
        RDF.type,
        SCHEMA.CreativeWork,
    ) in graph

    assert (
        doi_uri,
        SCHEMA.name,
        Literal("Example dataset"),
    ) in graph

    assert (
        doi_uri,
        G2R.resourceType,
        Literal("Dataset"),
    ) in graph

    assert (
        doi_uri,
        SCHEMA.publisher,
        Literal("Example Publisher"),
    ) in graph

    assert (
        doi_uri,
        SCHEMA.datePublished,
        Literal(2024, datatype=XSD.gYear),
    ) in graph


def test_build_graph_exports_doi_people() -> None:
    """Export creators and contributors associated with a DOI."""
    result = HarvestResult(
        organization="example",
        repositories=[],
        contributors=[],
        doi_records=[
            DOIRecord(
                doi="10.5281/example.789",
                title="Example work",
                resource_type="Software",
                publisher="Zenodo",
                publication_year=2025,
                creators=[
                    DOIContributor(
                        name="Alice Example",
                        orcid="0000-0002-1825-0097",
                    ),
                ],
                contributors=[
                    DOIContributor(
                        name="Bob Example",
                        orcid="0000-0003-1234-5678",
                        contributor_type="DataCurator",
                    ),
                ],
            ),
        ],
    )

    graph = build_graph(result)

    doi_uri = URIRef("https://doi.org/10.5281/example.789")

    creator_nodes = list(graph.objects(doi_uri, SCHEMA.creator))
    assert len(creator_nodes) == 1

    creator_node = creator_nodes[0]

    assert (
        creator_node,
        RDF.type,
        SCHEMA.Person,
    ) in graph

    assert (
        creator_node,
        SCHEMA.name,
        Literal("Alice Example"),
    ) in graph

    assert (
        creator_node,
        SCHEMA.identifier,
        URIRef("https://orcid.org/0000-0002-1825-0097"),
    ) in graph

    contributor_nodes = list(graph.objects(doi_uri, SCHEMA.contributor))
    assert len(contributor_nodes) == 1

    contributor_node = contributor_nodes[0]

    assert (
        contributor_node,
        SCHEMA.name,
        Literal("Bob Example"),
    ) in graph

    assert (
        contributor_node,
        G2R.contributorType,
        Literal("DataCurator"),
    ) in graph


def test_add_metadata_quality_measurements_creates_five_measurements() -> None:
    """Create one DQV measurement for each quality check."""
    record = DOIRecord(
        doi="10.5281/zenodo.1234567",
    )
    record.metadata_quality = check_metadata_quality(record)

    graph = Graph()
    record_uri = URIRef("https://doi.org/10.5281/zenodo.1234567")

    add_metadata_quality_measurements(
        graph,
        record,
        record_uri,
    )

    measurements = list(
        graph.objects(
            record_uri,
            DQV.hasQualityMeasurement,
        )
    )

    assert len(measurements) == 5


def test_quality_measurements_have_required_dqv_properties() -> None:
    """Add the required DQV properties to every measurement."""
    record = DOIRecord(
        doi="10.5281/zenodo.1234567",
    )
    record.metadata_quality = check_metadata_quality(record)

    graph = Graph()
    record_uri = URIRef("https://doi.org/10.5281/zenodo.1234567")

    add_metadata_quality_measurements(
        graph,
        record,
        record_uri,
    )

    measurements = list(
        graph.objects(
            record_uri,
            DQV.hasQualityMeasurement,
        )
    )

    assert len(measurements) == 5

    for measurement in measurements:
        assert (
            measurement,
            RDF.type,
            DQV.QualityMeasurement,
        ) in graph

        assert (
            measurement,
            DQV.computedOn,
            record_uri,
        ) in graph

        assert (
            measurement,
            DQV.isMeasurementOf,
            None,
        ) in graph

        assert (
            measurement,
            DQV.value,
            None,
        ) in graph


def test_quality_measurements_contain_all_checks_and_values() -> None:
    """Represent every quality check with its boolean result."""
    record = DOIRecord(
        doi="10.5281/zenodo.1234567",
    )
    record.metadata_quality = check_metadata_quality(record)

    graph = Graph()
    record_uri = URIRef("https://doi.org/10.5281/zenodo.1234567")

    add_metadata_quality_measurements(
        graph,
        record,
        record_uri,
    )

    expected_checks = {
        QUALITY.hasLicense: False,
        QUALITY.hasDescription: False,
        QUALITY.creatorsHaveOrcids: False,
        QUALITY.hasRelatedIdentifiers: False,
        QUALITY.hasFunding: False,
    }

    for check_uri, expected_value in expected_checks.items():
        measurements = list(
            graph.subjects(
                DQV.isMeasurementOf,
                check_uri,
            )
        )

        assert len(measurements) == 1

        measurement = measurements[0]
        value = graph.value(
            measurement,
            DQV.value,
        )

        assert value == Literal(
            expected_value,
            datatype=XSD.boolean,
        )


def test_quality_measurements_preserve_individual_results() -> None:
    """Export both passing and failing individual checks."""
    record = DOIRecord(
        doi="10.5281/zenodo.1234567",
    )

    quality = check_metadata_quality(record)
    assert quality.has_license is False
    assert quality.has_description is False

    record.metadata_quality = quality

    graph = Graph()
    record_uri = URIRef("https://doi.org/10.5281/zenodo.1234567")

    add_metadata_quality_measurements(
        graph,
        record,
        record_uri,
    )

    license_measurement = next(
        graph.subjects(
            DQV.isMeasurementOf,
            QUALITY.hasLicense,
        )
    )

    value = graph.value(
        license_measurement,
        DQV.value,
    )

    assert value == Literal(False, datatype=XSD.boolean)


def test_no_measurements_are_created_without_quality_result() -> None:
    """Skip measurements when quality has not been evaluated."""
    record = DOIRecord(
        doi="10.5281/zenodo.1234567",
    )

    graph = Graph()
    record_uri = URIRef("https://doi.org/10.5281/zenodo.1234567")

    add_metadata_quality_measurements(
        graph,
        record,
        record_uri,
    )

    measurements = list(
        graph.objects(
            record_uri,
            DQV.hasQualityMeasurement,
        )
    )

    assert measurements == []


def test_quality_measurement_values_are_xsd_booleans() -> None:
    """Serialize quality values as typed RDF booleans."""
    record = DOIRecord(
        doi="10.5281/zenodo.1234567",
    )
    record.metadata_quality = check_metadata_quality(record)

    graph = Graph()
    record_uri = URIRef("https://doi.org/10.5281/zenodo.1234567")

    add_metadata_quality_measurements(
        graph,
        record,
        record_uri,
    )

    measurement = next(
        graph.objects(
            record_uri,
            DQV.hasQualityMeasurement,
        )
    )

    value = graph.value(measurement, DQV.value)

    assert value == Literal(False, datatype=XSD.boolean)
