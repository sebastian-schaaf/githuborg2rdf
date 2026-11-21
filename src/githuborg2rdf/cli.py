"""CLI of githuborg2rdf."""

import typer

from githuborg2rdf.clients.github import GitHubApiError
from githuborg2rdf.lib import CalcOperation, calculate
from githuborg2rdf.pipeline import run_harvest

# create subcommand app
say = typer.Typer()

# create main app
app = typer.Typer()
app.add_typer(say, name="say")

# ----


@app.command()
def calc(op: CalcOperation, x: int, y: int):
    """Compute the result of applying an operation on x and y."""
    result: int = calculate(op, x, y)
    typer.echo(f"Result: {result}")


@app.command()
def harvest(organization: str) -> None:
    """Harvest contributors for a GitHub organization."""
    try:
        result = run_harvest(organization)
    except GitHubApiError as exc:
        typer.echo(f"GitHub API error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    contributors = result.contributors

    if not contributors:
        typer.echo(f"No contributors found for organization: {organization}")
        return

    for contributor in contributors:
        repositories = ", ".join(sorted(contributor.repositories))
        typer.echo(
            f"{contributor.login}: "
            f"{contributor.contributions} contributions "
            f"({repositories})"
        )


# ----


@say.command()
def hello(name: str):
    """Greet a person."""
    print(f"Hello {name}")


@say.command()
def goodbye(name: str, formal: bool = False):
    """Say goodbye to a person."""
    if formal:
        print(f"Goodbye {name}. Have a good day.")
    else:
        print(f"Bye {name}!")
