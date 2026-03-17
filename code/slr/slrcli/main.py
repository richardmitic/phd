import typer
from .join_annotated_data import app as join_app
from .slr_post_analysis import app as post_app

app = typer.Typer()

app.add_typer(join_app)
app.add_typer(post_app)

if __name__ == "__main__":
    app()