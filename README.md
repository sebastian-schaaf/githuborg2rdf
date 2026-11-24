# GitHubOrg2RDF

GitHubOrg2RDF generates an RDF knowledge graph from the public activity and
research-related metadata of a GitHub organization.

The pipeline combines information from GitHub, ORCID and DataCite. It retrieves
repositories and their non-bot contributors, attempts to match contributors to
ORCID records, collects related DOI metadata, evaluates selected metadata
quality criteria and exports the results as a Turtle-based RDF graph.

The resulting graph represents organizations, repositories, contributors,
research outputs, authors, related identifiers, funding information and
metadata-quality information. Repository-specific contributor relationships are
represented using `schema:contributor`, while organization membership is
represented separately using `schema:memberOf`.

The generated RDF can be used for exploration, visualization, metadata
analysis and further research on the relationship between software repositories,
contributors and research outputs.

## Installation

GitHubOrg2RDF requires Python 3.10 or newer.

Clone the repository and install the project with Poetry:

```bash
git clone https://github.com/sebastian-schaaf/githuborg2rdf.git
cd githuborg2rdf
poetry install
```

Alternatively, install the package directly from GitHub:

```bash
pip install git+https://github.com/sebastian-schaaf/githuborg2rdf.git
```

## Getting started

To export the data of a GitHub organization as an RDF graph, run:

```bash
poetry run githuborg2rdf-cli export Materials-Data-Science-and-Informatics
```

Replace `Materials-Data-Science-and-Informatics` with the name of the GitHub
organization to process.

The generated RDF graph is written as a Turtle file to:

```text
output/githuborg2rdf.ttl
```

The available command-line options can be displayed with:

```bash
poetry run githuborg2rdf-cli export --help
```

### Main processing steps

The `export` command performs the following steps:

1. Retrieve the repositories of the selected GitHub organization.
2. Retrieve the contributors of each repository.
3. Exclude bot accounts from the contributor data.
4. Preserve repository-specific contributor relationships.
5. Aggregate contributor information across repositories.
6. Match contributors to ORCID records where possible.
7. Retrieve related DOI records and their metadata from DataCite.
8. Calculate selected metadata-quality measurements for DOI records.
9. Export the collected information as an RDF graph in Turtle format.

The resulting Turtle file can be visualized in an instance of [`rdf-graph-visualization`](https://github.com/Materials-Data-Science-and-Informatics/rdf-graph-visualization). In this case, please find a configuration yml file in the following directory:

```text
vis_config/config.yml
```
Just copy the config file into the base directory of your rdf-graph-visualization instance.

### RDF relationships

The generated RDF graph includes relationships such as:

```text
Repository  --schema:isPartOf-----> Organization
Repository  --schema:contributor--> Person
Person      --schema:memberOf------> Organization
Dataset     --schema:creator-------> Person
Dataset     --schema:relatedLink---> Repository
```

The precise set of properties depends on the metadata returned by GitHub,
ORCID and DataCite.

## Data sources

GitHubOrg2RDF uses publicly available metadata from the following services:

- [GitHub](https://github.com/) for organizations, repositories and
  contributors.
- [ORCID](https://orcid.org/) for contributor identification and researcher
  metadata.
- [DataCite](https://datacite.org/) for DOI records and associated research
  metadata.

The completeness of the generated graph depends on the information available
from these services at the time of the export.

## Metadata quality

GitHubOrg2RDF calculates selected quality measurements for DOI metadata. These
measurements help identify the completeness of relevant metadata fields and
provide an initial indication of metadata quality.

The quality measurements are intended to support exploration and analysis.
They should not be interpreted as a complete or authoritative assessment of
the quality of a DOI record.

## Limitations

The generated RDF graph is an enriched view of publicly available metadata. It
is not intended to be a complete or authoritative record of all software
contributions, researchers or research outputs.

Contributor-to-ORCID matching depends on the identifiers and metadata available
from the respective services. A missing ORCID match does not imply that a
contributor has no ORCID record.

Similarly, the absence of a DOI record or metadata field does not imply that no
corresponding research output or information exists.

The availability and completeness of the generated data may also be affected
by API rate limits, service availability and changes to the APIs of GitHub,
ORCID or DataCite.

## Development

Install the project and its development dependencies with:

```bash
poetry install
```

Run the test suite with:

```bash
poetry run pytest
```

Run the configured pre-commit checks with:

```bash
poetry run pre-commit run --all-files
```

The test suite covers the clients, pipeline, metadata-quality measurements,
command-line interface and RDF export.

## Troubleshooting

### Installation fails with `IndexError: list index out of range`

Check the installed version of `pip`:

```bash
python -m pip --version
```

Upgrade `pip` if necessary:

```bash
python -m pip install --upgrade pip
```

Then try installing the project again.

### API requests fail

If requests to an external API fail, check the following:

- the GitHub organization name is correct;
- the required API credentials are configured;
- the external service is available;
- API rate limits have not been exceeded;
- installed dependencies are up to date.

To display the available command-line options, run:

```bash
poetry run githuborg2rdf-cli export --help
```

### The output file is not where expected

The default output file is:

```text
output/githuborg2rdf.ttl
```

Make sure that the command is executed from the root directory of the project
and that the export completes without errors.

## License

GitHubOrg2RDF is released under the MIT License. See the
[`LICENSE`](LICENSE) file for the complete license text.

## How to cite

If you use GitHubOrg2RDF in a scientific publication, please cite the project
using the [`CITATION.cff`](CITATION.cff) file included in this repository.

The citation metadata can be used with tools that support the
[Citation File Format](https://citation-file-format.github.io/).

## Acknowledgements

This project builds on the work and support of several people and
organizations.

Special thanks go to:

- **Volker Hofmann** for the inspiring project idea and the opportunity to
  present this work.
- **Mustafa Soylu** and **Anton Pirogov** for developing the
  [`fair-python-cookiecutter`](https://github.com/Materials-Data-Science-and-Informatics/fair-python-cookiecutter)
  project, which provided the foundation for this Python project.
- **Mustafa Soylu** for developing the
  [`rdf-graph-visualization`](https://github.com/Materials-Data-Science-and-Informatics/rdf-graph-visualization)
  project.
- The **Institute for Materials Data Science and Informatics (IAS-9)** at
  [Forschungszentrum Jülich](https://fz-juelich.de/ias/ias-9/) for its
  extensive preparatory work and for publishing numerous software solutions
  under open-source licenses.
