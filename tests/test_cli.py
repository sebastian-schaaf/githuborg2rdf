"""Tests for the CLI."""

from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st
from typer.testing import CliRunner

from githuborg2rdf.cli import app
from githuborg2rdf.clients.github import GitHubApiError
from githuborg2rdf.models import Contributor

runner = CliRunner()


def test_calc_addition():
    result = runner.invoke(app, ["calc", "add", "20", "22"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "Result: 42"


def test_harvest() -> None:
    """Print harvested contributors."""
    contributors = [
        Contributor(
            login="alice",
            html_url="https://github.com/alice",
            contributions=8,
            repositories={"repo-one", "repo-two"},
        ),
        Contributor(
            login="bob",
            html_url="https://github.com/bob",
            contributions=1,
            repositories={"repo-one"},
        ),
    ]

    with patch(
        "githuborg2rdf.cli.run_harvest",
        return_value=contributors,
    ) as mock_harvest:
        result = runner.invoke(app, ["harvest", "example"])

    assert result.exit_code == 0
    assert "alice: 8 contributions (repo-one, repo-two)" in result.stdout
    assert "bob: 1 contributions (repo-one)" in result.stdout
    mock_harvest.assert_called_once_with("example")


def test_harvest_without_contributors() -> None:
    """Report when no contributors are found."""
    with patch(
        "githuborg2rdf.cli.run_harvest",
        return_value=[],
    ):
        result = runner.invoke(app, ["harvest", "example"])

    assert result.exit_code == 0
    assert "No contributors found" in result.stdout


def test_harvest_handles_github_api_error() -> None:
    """Return a nonzero exit code for GitHub API errors."""
    with patch(
        "githuborg2rdf.cli.run_harvest",
        side_effect=GitHubApiError("connection failed"),
    ):
        result = runner.invoke(app, ["harvest", "example"])

    assert result.exit_code == 1
    assert "GitHub API error: connection failed" in result.stderr


person_names = ["Jane", "John"]


@pytest.mark.parametrize(
    "name, formal",
    [(name, formal) for name in person_names for formal in [False, True]],
)
def test_goodbye(name: str, formal: bool):
    args = ["say", "goodbye", name]
    if formal:
        args += ["--formal"]

    result = runner.invoke(app, args)

    assert result.exit_code == 0
    assert name in result.stdout
    if formal:
        assert "good day" in result.stdout


# Example of hypothesis auto-generated inputs,
# here the names are generated from a regular expression.

# NOTE: this is not really a good regex for names!
person_name_regex = r"^[A-Z]\w+$"


@given(st.from_regex(person_name_regex))
def test_hello(name: str):
    result = runner.invoke(app, ["say", "hello", name])

    assert result.exit_code == 0
    assert f"Hello {name}" in result.stdout
