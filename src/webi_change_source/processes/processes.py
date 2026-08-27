import logging
from datetime import datetime
from threading import current_thread

import sqlalchemy as sql
from sqlalchemy import orm as sql_orm

from webi_change_source import api_backend
from webi_change_source.SettingsManager import SettingsManager
from webi_change_source.db_backend import DataProvider, Conversion, populate_document_record, \
    populate_dataprovider_records

logger: logging.Logger = logging.getLogger(__name__)


def update_document_and_dataprovider_records(
    document_id: int,
    settings_manager: SettingsManager,
    session_maker: sql_orm.sessionmaker,
) -> bool:
    func_logger: logging.Logger = logger.getChild("update_document_and_dataprovider_records")

    func_logger.debug(f"Updating document records for {document_id}")
    doc_success: bool = populate_document_record(document_id, settings_manager, session_maker)
    func_logger.info(f"Updated document record for {document_id} : {"True" if doc_success else "False"}")

    dp_success: bool = False
    if doc_success:
        func_logger.debug(f"Updating dataprovider records for {document_id}")
        dp_success = populate_dataprovider_records(document_id, settings_manager, session_maker)
        func_logger.info(f"Updated data provider records for {document_id} : {"True" if dp_success else "False"}")
    return doc_success and dp_success


def process_and_perform_conversion(
    document_id: int,
    batch_no: int,
    settings_manager: SettingsManager,
    session_maker: sql_orm.sessionmaker,
) -> bool:
    with session_maker() as thread_session:
        func_logger: logging.Logger = logger.getChild("process_and_perform_conversion")
        func_logger = func_logger.getChild(current_thread().name)

        number_of_failures: int = 0

        stmt: sql.Select[tuple[DataProvider]] = sql.select(DataProvider).where(DataProvider.document_id == document_id)

        dp: DataProvider
        for dp in thread_session.scalars(stmt):
            try:

                conversion: Conversion = Conversion(
                    batch_no=batch_no,
                    query_id=dp.id,
                    document_id=dp.document_id,
                    conversion_date=datetime.today(),
                    status_dp_details="OK"
                )

                if dp.data_source_type != "unv" or dp.data_source_id != settings_manager.old_universe_id:
                    conversion.status_dp_correct_source = "No"
                    func_logger.debug("status_dp_correct_source = No")
                    continue

                conversion.status_dp_correct_source = "Yes"
                func_logger.info("status_dp_correct_source = Yes")

                thread_session.add(conversion)

                conversion.status_mappings = "Retrieving"
                func_logger.debug("status_mappings = Retrieving")

                with api_backend.APILogonManager(settings_manager) as logon_token:
                    mappings_list: list[dict] | None
                    mappings_str: str | None
                    mappings_list, mappings_str = api_backend.get_data_provider_mappings(
                        dp.document_id,
                        dp.id,
                        settings_manager,
                        logon_token
                    )

                if mappings_str is None or mappings_list is None:
                    conversion.status_mappings = "No mappings retrieved"
                    logger.error("status_mappings = No mappings retrieved")
                    number_of_failures += 1
                    continue

                if sum([1 for x in mappings_list if x["@status"] != "Ok"]):
                    conversion.status_mappings = f"Issue with at least one mapped column: {mappings_list!r}"
                    func_logger.error(f"status_mappings = Issue with at least one mapped column: {mappings_list!r}")
                    number_of_failures += 1
                    continue

                conversion.status_mappings = "Success"
                func_logger.info("status_mappings = Success")

                conversion.status_change_source = "Starting"
                func_logger.debug("status_change_source = Starting")

                with api_backend.APILogonManager(settings_manager) as logon_token:
                    ok: bool
                    change_dict: dict | None
                    ok, change_dict = api_backend.change_data_provider_mappings(
                        dp.document_id,
                        dp.id,
                        mappings_str,
                        settings_manager,
                        logon_token
                    )

                    if not ok:
                        conversion.status_change_source = f"Encountered error in change source: {change_dict!r}"
                        func_logger.error(f"status_change_source = Encountered error in change source: {change_dict!r}")
                        number_of_failures += 1
                        break

                    conversion.status_change_source = "Success"
                    func_logger.info("status_change_source = Success")

                    conversion.status_save = "No save needed"

                    conversion.status_unload = "Unloading"
                    func_logger.debug("status_unload = Unloading")
                    unload_success: bool = api_backend.set_document_unused(
                        dp.document_id,
                        settings_manager,
                        logon_token
                    )

                    conversion.status_unload = "Successful" if unload_success else "Unsuccessful"
                    logger.info(f"status_unload = {conversion.status_unload}")

            except Exception as e:
                number_of_failures += 1
                logger.error(f"Error during change source process: {e}")

            finally:
                thread_session.commit()

        try:
            success = update_document_and_dataprovider_records(document_id, settings_manager, session_maker)
            if not success:
                logger.error(f"Error in updating document details after change source")
        except Exception as e:
            logger.error(f"Error in updating document details after change source: {e}")

        return number_of_failures > 0
