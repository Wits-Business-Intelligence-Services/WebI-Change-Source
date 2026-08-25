import typer

from webi_change_source.main import main

app = typer.Typer()
app.command()(main)

if __name__ == '__main__':
    app()
