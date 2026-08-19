import logging
from datetime import datetime, UTC

import sqlalchemy as sql
from sqlalchemy import orm as sql_orm

import api_backend
from SettingsManager import SettingsManager
from .orm_models import DataProvider, Document


def populate_document_record(document_id: int, settings_manager: SettingsManager, logger: logging.Logger,
                             db_engine: sql.Engine) -> None:
    logger.info(f"Getting base record template for {document_id}")

    # doc_record: ConversionRecord = ConversionRecord(id, *["" for _ in range(12)])

    with api_backend.APILogonManager(settings_manager, logger) as logon_token:
        doc_details: dict | None = api_backend.get_document_details(
            document_id, settings_manager, logon_token, logger
        )
    with sql_orm.Session(db_engine) as session:
        stmt = sql.select(Document).where(Document.id == document_id)

        if doc_details is None:
            if session.scalars(stmt).one_or_none() is not None:
                # Perform an update
                doc = session.scalars(stmt).one()
                doc.status = "MISSING"
            else:
                # Create new record
                doc: Document = Document(
                    id=document_id,
                    name="UNKNOWN DOCUMENT",
                    last_updated=datetime.fromtimestamp(0, tz=UTC),
                    status="UNKNOWN"
                )
                session.add(doc)

        else:
            if session.scalars(stmt).one_or_none() is not None:
                # Perform an update
                doc = session.scalars(stmt).one()
                doc.name = doc_details["name"]
                doc.last_updated = datetime.fromisoformat(doc_details["updated"])
                doc.status = "OK"
            else:
                # Create new record
                doc: Document = Document(
                    id=document_id,
                    name=doc_details["name"],
                    last_updated=datetime.fromisoformat(doc_details["updated"]),
                    status="OK",
                )
                session.add(doc)

        session.commit()


def populate_dataprovider_records(document_id: int, settings_manager: SettingsManager, logger: logging.Logger,
                                  db_engine: sql.Engine) -> None:
    logon_token: str
    with api_backend.APILogonManager(settings_manager, logger) as logon_token:
        # print(f"Attempting to get data providers for BO ID: {id}")
        dp_list: list[api_backend.DataProviderQueryResult] | None = api_backend.get_all_data_provider_details(
            document_id, settings_manager, logon_token, logger
        )

    if dp_list is None or len(dp_list) == 0:
        return

    with sql_orm.Session(db_engine) as session:
        for dp_result in dp_list:
            stmt = sql.select(DataProvider).where(
                DataProvider.id == dp_result.id).where(DataProvider.document_id == document_id)

            if session.scalars(stmt).one_or_none() is not None:
                # Perform an update
                dp: DataProvider = session.scalars(stmt).one()
                dp.data_source_id = dp_result.data_source_id
                dp.data_source_type = dp_result.data_source_type
                dp.name = dp_result.name

            else:
                # Create new record
                dp: DataProvider = DataProvider(
                    id=dp_result.id,
                    document_id=document_id,
                    name=dp_result.name,
                    data_source_id=dp_result.data_source_id,
                    data_source_original_type=dp_result.data_source_type,
                    data_source_type=dp_result.data_source_type
                )
                session.add(dp)

        session.commit()
