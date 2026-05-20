import typer


app = typer.Typer(name="kuba", help="Kuba folktale video pipeline.")


@app.callback()
def main() -> None:
    """Kuba folktale video pipeline."""
