import json
import tempfile
from pathlib import Path

import typer

from extractor import extract_with_retry
from validators import validate

app = typer.Typer(help="Extract structured data from receipt images.")


@app.command()
def extract(image: Path = typer.Argument(..., exists=True, dir_okay=False)):
    """Extract a receipt and print validated JSON."""
    with tempfile.TemporaryDirectory() as tmp:
        _, final, record = extract_with_retry(image, Path(tmp) / "first", Path(tmp) / "retry")

    if final is None:
        typer.echo("Extraction failed: the model output could not be parsed.", err=True)
        raise typer.Exit(code=1)

    output = {
        "receipt": json.loads(final.model_dump_json()),
        "validation": validate(final),
        "retried": record["retried"],
    }
    typer.echo(json.dumps(output, indent=2))


if __name__ == "__main__":
    app()