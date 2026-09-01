import concurrent.futures
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from os import makedirs
from pathlib import Path

import rich
import sqlalchemy as sql
import sqlalchemy.orm as sql_orm
from tqdm import tqdm

from webi_change_source.db_backend import *
from webi_change_source.processes import *
from webi_change_source.settings import *

logger: logging.Logger = logging.getLogger(__name__)


def main(
    webi_document_list_path: str,
    update_document_data: bool,
    perform_change_source: bool,
    num_workers: int,
):
    settings_file_path: Path = Path("./settings.toml")

    if not settings_file_path.exists():
        with open(settings_file_path, "w") as new_settings_file:
            with open(settings_template_path, "r") as settings_template_file:
                settings_template: list[str] = settings_template_file.readlines()

            new_settings_file.writelines(settings_template)

        rich.print("Please populate [bold magenta]./settings.toml[/bold magenta] with your settings.")
        raise SystemExit

    settings_manager: SettingsManager = SettingsManager(
        Path("./settings.toml"),
        webi_document_list_path,
        update_document_data,
        perform_change_source,
        num_workers
    )

    makedirs(Path("./logs"), exist_ok=True)

    log_file_path: Path = Path(
        "./logs/conversion_log_" + str(datetime.today()).replace(" ", "_").replace(":", "_") + ".log").absolute()

    logging.basicConfig(
        filename=log_file_path,
        encoding='utf-8',
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    func_logger: logging.Logger = logger.getChild("main")

    db_engine: sql.Engine = sql.create_engine("sqlite:///db.sqlite", echo=False)
    session_maker: sql_orm.sessionmaker = sql_orm.sessionmaker(db_engine)

    Base.metadata.create_all(db_engine)

    if settings_manager.update_document_data:

        # Get base records for db
        with tqdm(total=len(settings_manager.document_list)) as pbar:

            total_failures: int = 0

            if settings_manager.num_workers == 1:
                document_id: int
                for document_id in settings_manager.document_list:
                    try:
                        update_document_and_dataprovider_records(document_id, settings_manager, session_maker)
                    except Exception as e:
                        total_failures += 1
                        func_logger.error(
                            f"update_document_and_dataprovider_records failed for document {document_id}: {e}")
                    finally:
                        pbar.update(1)
                        pbar.set_description(f"Gathering info - Total failures: {total_failures}")

            else:
                with ThreadPoolExecutor(max_workers=settings_manager.num_workers) as executor:

                    futures: dict[concurrent.futures.Future, int] = {
                        executor.submit(
                            lambda
                                x: update_document_and_dataprovider_records(x, settings_manager, session_maker),
                            doc_id
                        ): doc_id
                        for doc_id in settings_manager.document_list
                    }
                    initial_db_population_results: dict[int, bool] = {}
                    for future in concurrent.futures.as_completed(futures):
                        doc_id = futures[future]
                        if not future.exception():
                            initial_db_population_results[doc_id] = future.result()
                            if not initial_db_population_results[doc_id]:
                                total_failures += 1
                                func_logger.error(
                                    f"update_document_and_dataprovider_records failed for document {doc_id}")
                        else:
                            total_failures += 1
                            func_logger.error(
                                f"update_document_and_dataprovider_records failed for document {doc_id}: {future.exception()}")
                        pbar.update(1)
                        pbar.set_description(f"Gathering info - Total failures: {total_failures}")

                # Run in serial for any that failed above
                document_id: int
                for document_id in [doc_id for doc_id, status_success in initial_db_population_results.items() if
                                    status_success == False]:
                    populate_document_record(document_id, settings_manager, session_maker)
                    populate_dataprovider_records(document_id, settings_manager, session_maker)

    if settings_manager.perform_change_source:
        with sql_orm.Session(db_engine) as session:

            batch_no_stmt = sql.select(sql.func.max(Conversion.batch_no))
            batch_no_stmt_result: int | None = session.scalars(batch_no_stmt).one_or_none()
            batch_no = batch_no_stmt_result + 1 if batch_no_stmt_result is not None else 1

        with tqdm(total=len(settings_manager.document_list)) as pbar:
            with ThreadPoolExecutor(max_workers=settings_manager.num_workers) as executor:

                total_failures: int = 0

                futures: dict[concurrent.futures.Future, int] = {
                    executor.submit(
                        lambda
                            x: process_and_perform_conversion(x, batch_no, settings_manager, session_maker),
                        doc_id
                    ): doc_id
                    for doc_id in settings_manager.document_list
                }
                conversion_results: dict[int, bool] = {}
                for future in concurrent.futures.as_completed(futures):
                    doc_id: int = futures[future]

                    if not future.exception():
                        conversion_results[doc_id] = future.result()
                        total_failures += conversion_results[doc_id]
                    else:
                        total_failures += 1

                    pbar.update(1)
                    pbar.set_description(f"Converting - Total failures: {total_failures}")
