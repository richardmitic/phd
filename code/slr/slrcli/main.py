import typer

from .search_semantic_scholar import app as search_app
from .ingest_raw_data import app as ingest_app
from .join_annotated_data import app as join_app
from .slr_post_analysis import app as post_app
from .prepare_submission import app as prep_app

app = typer.Typer()

app.add_typer(search_app)
app.add_typer(ingest_app)
app.add_typer(join_app)
app.add_typer(post_app)
app.add_typer(prep_app)

if __name__ == "__main__":
    app()