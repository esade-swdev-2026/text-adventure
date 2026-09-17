import typer

app = typer.Typer(help="Replace this with your project's command-line interface.")


@app.command()
def greet(name: str, count: int = 1) -> None:
    if count < 1:
        typer.echo("count must be at least 1", err=True)
        raise typer.Exit(code=1)
    for _ in range(count):
        typer.echo(f"Hello, {name}!")


@app.command()
def bye(name: str) -> None:
    typer.echo(f"Goodbye, {name}.")


if __name__ == "__main__":
    app()
