"""Build RDF graphs from harvested GitHub organization data."""

from rdflib import Graph

from githuborg2rdf.models import HarvestResult


def build_graph(result: HarvestResult) -> Graph:
    """Build an RDF graph from a complete harvest result."""
    return Graph()
