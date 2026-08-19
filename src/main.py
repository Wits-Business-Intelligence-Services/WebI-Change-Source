import logging
from datetime import datetime
from pathlib import Path

import sqlalchemy as sql
import sqlalchemy.orm as sql_orm

import api_backend
from SettingsManager import SettingsManager
from db_backend import *


def main(settings_manager: SettingsManager, logger: logging.Logger):
    db_engine: sql.Engine = sql.create_engine("sqlite:///db.sqlite", echo=False)

    Base.metadata.create_all(db_engine)

    # Get base record templates
    document_id: int
    for document_id in settings_manager.document_list:
        populate_document_record(document_id, settings_manager, logger, db_engine)
        populate_dataprovider_records(document_id, settings_manager, logger, db_engine)

    with sql_orm.Session(db_engine) as session:

        batch_no_stmt = sql.select(sql.func.max(Conversion.batch_no))
        batch_no_stmt_result: int | None = session.scalars(batch_no_stmt).one_or_none()
        batch_no = batch_no_stmt_result + 1 if batch_no_stmt_result is not None else 1

        # Process and perform conversions
        for document_id in settings_manager.document_list:

            doc_stmt = sql.select(Document).where(Document.id == document_id)

            document: Document = session.scalars(doc_stmt).one()

            print(repr(document))

            stmt = sql.select(DataProvider).where(DataProvider.document_id == document_id)

            dp: DataProvider
            for dp in session.scalars(stmt):
                try:
                    print(repr(dp))

                    conversion: Conversion = Conversion(
                        batch_no=batch_no,
                        query_id=dp.id,
                        document_id=dp.document_id,
                        conversion_date=datetime.today(),
                        status_dp_details="OK"
                    )

                    # print(f"Processing the following data provider: {dp}")

                    if dp.data_source_type != "unv" and dp.data_source_id != settings_manager.old_universe_id:
                        # print(f"DP {dp.id_dp} is not of type unv")
                        conversion.status_dp_correct_source = "No"
                        continue

                    conversion.status_dp_correct_source = "Yes"

                    session.add(conversion)

                    # print("Getting mappings")
                    conversion.status_mappings = "Retrieving"

                    with api_backend.APILogonManager(settings_manager, logger) as logon_token:
                        mappings_list: list[str] | None
                        mappings_str: str | None
                        mappings_list, mappings_str = api_backend.get_data_provider_mappings(
                            dp.document_id,
                            dp.id,
                            settings_manager,
                            logon_token, logger
                        )

                    if mappings_str is None or mappings_list is None:
                        # print("No mappings retrieved")
                        conversion.status_mappings = "No mappings retrieved"
                        continue

                    # print(mappings_str)

                    if sum([1 for x in mappings_list if x["@status"] != "Ok"]):
                        # print("Issue with at least one mapped column")
                        conversion.status_mappings = f"Issue with at least one mapped column: {mappings_list!r}"
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
                    print(repr(conversion))


                except Exception as e:
                    session.rollback()
                    raise e
                finally:
                    session.commit()

            # base_doc_records.extend(dp_records)

            # print(f"Logoff {"successful" if logoff_success else "unsuccessful"}")


if __name__ == '__main__':
    sm: SettingsManager = SettingsManager(Path("./settings.toml"))

    log_file_path: Path = Path(
        "./logs/conversion_log_" + str(datetime.today()).replace(" ", "_").replace(":", "_") + ".log")

    lgr: logging.Logger = logging.getLogger(__name__)
    logging.basicConfig(filename=log_file_path, encoding='utf-8', level=logging.DEBUG)

    main(sm, lgr)
