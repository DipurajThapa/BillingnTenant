"""C1 command entry point."""

import typer

from preflight import __version__

app = typer.Typer(no_args_is_help=True)


@app.callback()
def root() -> None:
    """Run deterministic SaaS preflight checks."""


@app.command()
def version() -> None:
    """Print package version."""
    typer.echo(__version__)


def main() -> None:
    app()
