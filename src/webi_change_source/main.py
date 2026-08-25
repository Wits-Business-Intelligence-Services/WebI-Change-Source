import concurrent
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import current_thread

import sqlalchemy as sql
import sqlalchemy.orm as sql_orm
from tqdm import tqdm

from webi_change_source import api_backend
from webi_change_source.SettingsManager import SettingsManager
from webi_change_source.db_backend import *


def process_and_perform_conversion(
        document_id: int,
        batch_no: int,
        settings_manager: SettingsManager,
        session_maker: sql_orm.sessionmaker
) -> bool:
    with session_maker() as thread_session:
        logger: logging.Logger = logging.getLogger(f"{__name__}.{current_thread().name}")

        number_of_failures: int = 0

        stmt = sql.select(DataProvider).where(DataProvider.document_id == document_id)

        dp: DataProvider
        for dp in thread_session.scalars(stmt):
            try:
                # print(repr(dp))

                conversion: Conversion = Conversion(
                    batch_no=batch_no,
                    query_id=dp.id,
                    document_id=dp.document_id,
                    conversion_date=datetime.today(),
                    status_dp_details="OK"
                )

                # print(f"Processing the following data provider: {dp}")

                if dp.data_source_type != "unv" or dp.data_source_id != settings_manager.old_universe_id:
                    # print(f"DP {dp.id_dp} is not of type unv")
                    conversion.status_dp_correct_source = "No"
                    continue

                conversion.status_dp_correct_source = "Yes"

                thread_session.add(conversion)

                # print("Getting mappings")
                conversion.status_mappings = "Retrieving"

                with api_backend.APILogonManager(settings_manager, logger) as logon_token:
                    mappings_list: list[dict] | None
                    mappings_str: str | None
                    mappings_list, mappings_str = api_backend.get_data_provider_mappings(
                        dp.document_id,
                        dp.id,
                        settings_manager,
                        logon_token,
                        logger
                    )

                if mappings_str is None or mappings_list is None:
                    # print("No mappings retrieved")
                    conversion.status_mappings = "No mappings retrieved"
                    number_of_failures += 1
                    continue

                # print(mappings_str)

                if sum([1 for x in mappings_list if x["@status"] != "Ok"]):
                    # print("Issue with at least one mapped column")
                    conversion.status_mappings = f"Issue with at least one mapped column: {mappings_list!r}"
                    number_of_failures += 1
                    continue

                # print("No issues found in mappings")
                conversion.status_mappings = "Success"

                # print("Attempting to change source")
                conversion.status_change_source = "Starting"

                with api_backend.APILogonManager(settings_manager, logger) as logon_token:
                    change_dict: dict | None
                    ok, change_dict, _ = api_backend.change_data_provider_mappings(
                        dp.document_id,
                        dp.id,
                        mappings_str,
                        settings_manager,
                        logon_token, logger
                    )

                    if not ok:
                        # print("Encountered error in change source")
                        conversion.status_change_source = f"Encountered error in change source: {change_dict!r}"
                        number_of_failures += 1
                        break

                    # modified_dps.append(dp.id_dp)

                    # print("Successfully changed source")
                    conversion.status_change_source = "Success"

                    # print("Saving changes to document")
                    conversion.status_save = "Saving"

                    save_success: bool = api_backend.save_changes_to_document(
                        dp.document_id,
                        settings_manager,
                        logon_token, logger
                    )
                    if not save_success:
                        number_of_failures += 1

                    # print(f"Save {"successful" if save_success else "unsuccessful"}")
                    conversion.status_save = "Successful" if save_success else "Unsuccessful"

                    conversion.status_unload = "Unloading"
                    unload_success: bool = api_backend.set_document_unused(
                        dp.document_id,
                        settings_manager,
                        logon_token, logger
                    )

                # print(f"Unload {"successful" if unload_success else "unsuccessful"}")
                conversion.status_unload = "Successful" if unload_success else "Unsuccessful"

                # dp_records.append(dp_record)
                # print(repr(conversion))


            except Exception as e:
                thread_session.rollback()
                raise e
            finally:
                thread_session.commit()

        return number_of_failures > 0

        # base_doc_records.extend(dp_records)

        # print(f"Logoff {"successful" if logoff_success else "unsuccessful"}")


def document_and_dataprovider_records(
        document_id: int,
        settings_manager: SettingsManager,
        logger: logging.Logger,
        session_maker: sql_orm.sessionmaker
) -> bool:
    doc_success: bool = populate_document_record(document_id, settings_manager, logger, session_maker)
    dp_success: bool = False
    if doc_success:
        dp_success = populate_dataprovider_records(document_id, settings_manager, logger, session_maker)
    return doc_success and dp_success


def main():
    settings_manager: SettingsManager = SettingsManager(Path("./settings.toml"))

    log_file_path: Path = Path(
        "./logs/conversion_log_" + str(datetime.today()).replace(" ", "_").replace(":", "_") + ".log").absolute()

    logger: logging.Logger = logging.getLogger(__name__)
    logging.basicConfig(
        filename=log_file_path,
        encoding='utf-8',
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    db_engine: sql.Engine = sql.create_engine("sqlite:///db.sqlite", echo=False)
    session_maker: sql_orm.sessionmaker = sql_orm.sessionmaker(db_engine)

    Base.metadata.create_all(db_engine)

    num_workers: int = 8
    gather_initial_db_data: bool = False
    perform_conversions: bool = True

    if gather_initial_db_data:

        # Get base records for db
        with tqdm(total=len(settings_manager.document_list)) as pbar:
            with ThreadPoolExecutor(max_workers=num_workers) as executor:

                futures: dict[concurrent.futures.Future, int] = {
                    executor.submit(
                        lambda x: document_and_dataprovider_records(x, settings_manager, logger, session_maker),
                        doc_id
                    ): doc_id
                    for doc_id in settings_manager.document_list
                }
                initial_db_population_results: dict[int, bool] = {}
                for future in concurrent.futures.as_completed(futures):
                    doc_id = futures[future]
                    if not future.exception():
                        initial_db_population_results[doc_id] = future.result()
                    pbar.update(1)

        # Run in serial for any that failed above
        document_id: int
        for document_id in [doc_id for doc_id, status_success in initial_db_population_results.items() if
                            status_success == False]:
            populate_document_record(document_id, settings_manager, logger, session_maker)
            populate_dataprovider_records(document_id, settings_manager, logger, session_maker)

    if perform_conversions:
        with sql_orm.Session(db_engine) as session:

            batch_no_stmt = sql.select(sql.func.max(Conversion.batch_no))
            batch_no_stmt_result: int | None = session.scalars(batch_no_stmt).one_or_none()
            batch_no = batch_no_stmt_result + 1 if batch_no_stmt_result is not None else 1

        with tqdm(total=len(settings_manager.document_list)) as pbar:
            with ThreadPoolExecutor(max_workers=num_workers) as executor:

                total_failures: int = 0

                futures: dict[concurrent.futures.Future, int] = {
                    executor.submit(
                        lambda x: process_and_perform_conversion(x, batch_no, settings_manager, session_maker),
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
                    pbar.set_description(f"Total_failures: {total_failures}")
