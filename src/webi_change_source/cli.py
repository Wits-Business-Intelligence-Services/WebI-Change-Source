from typing import Annotated

import typer

from webi_change_source.main import main

app = typer.Typer()


@app.command()
def update_local_document_db(
    webi_document_list_path: Annotated[
        str, typer.Argument(help="Relative path to file with list of WebI document IDs")],
    num_workers: Annotated[int, typer.Option(help="Run process in parallel up with up to 8 workers")] = 1,
) -> None:
    main(
        webi_document_list_path,
        True,
        False,
        num_workers
    )


@app.command()
def perform_change_source(
    webi_document_list_path: Annotated[
        str, typer.Argument(help="Relative path to file with list of WebI document IDs")],
    num_workers: Annotated[int, typer.Option(help="Run process in parallel up with up to 8 workers")] = 1,
) -> None:
    main(
        webi_document_list_path,
        False,
        True,
        num_workers
    )


@app.command()
def full_pipeline(
    webi_document_list_path: Annotated[
        str, typer.Argument(help="Relative path to file with list of WebI document IDs")],
    num_workers: Annotated[int, typer.Option(help="Run process in parallel up with up to 8 workers")] = 1,
) -> None:
    main(
        webi_document_list_path,
        True,
        True,
        num_workers
    )


if __name__ == '__main__':
    app()
