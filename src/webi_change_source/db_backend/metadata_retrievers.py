import logging
from datetime import datetime, UTC

import sqlalchemy as sql
from sqlalchemy import orm as sql_orm

from webi_change_source import api_backend
from webi_change_source.settings import SettingsManager
from .orm_models import DataProvider, Document

logger: logging.Logger = logging.getLogger(__name__)


def populate_document_record(
    document_id: int,
    settings_manager: SettingsManager,
    session_maker: sql_orm.sessionmaker,
) -> bool:
    func_logger: logging.Logger = logger.getChild("populate_document_record")

    func_logger.info(f"Getting base record template for {document_id}")

    with api_backend.APILogonManager(settings_manager) as logon_token:
        doc_details: dict | None = api_backend.get_document_details(document_id, settings_manager, logon_token)
        if doc_details is None:
            warn_msg: str = f"Failed to retrieve document details for: {document_id}"
            # print(warn_msg)
            func_logger.warning(warn_msg)
    with session_maker() as session:
        try:
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
                        name="UNKNOWN",
                        path="UNKNOWN",
                        created_by="UNKNOWN",
                        last_author="UNKNOWN",
                        last_updated=datetime.fromtimestamp(0, tz=UTC),
                        status="MISSING"
                    )
                    session.add(doc)
                output_status = False
            else:
                if session.scalars(stmt).one_or_none() is not None:
                    # Perform an update
                    doc = session.scalars(stmt).one()
                    doc.name = doc_details["name"] if "name" in doc_details else "UNKNOWN"
                    doc.path = doc_details["path"] if "path" in doc_details else "UNKNOWN"
                    doc.created_by = doc_details["createdBy"] if "createdBy" in doc_details else "UNKNOWN"
                    doc.last_author = doc_details["lastAuthor"] if "lastAuthor" in doc_details else "UNKNOWN"
                    doc.last_updated = datetime.fromisoformat(
                        doc_details["updated"]) if "updated" in doc_details else datetime.fromtimestamp(0, tz=UTC)
                    doc.status = "OK"
                else:
                    # Create new record
                    doc: Document = Document(
                        id=document_id,
                        name=doc_details["name"] if "name" in doc_details else "UNKNOWN",
                        path=doc_details["path"] if "path" in doc_details else "UNKNOWN",
                        created_by=doc_details["createdBy"] if "createdBy" in doc_details else "UNKNOWN",
                        last_author=doc_details["lastAuthor"] if "lastAuthor" in doc_details else "UNKNOWN",
                        last_updated=datetime.fromisoformat(
                            doc_details["updated"]) if "updated" in doc_details else datetime.fromtimestamp(0, tz=UTC),
                        status="OK",
                    )
                    session.add(doc)
                output_status = True
        finally:
            session.commit()

        return output_status


def populate_dataprovider_records(
    document_id: int,
    settings_manager: SettingsManager,
    session_maker: sql_orm.sessionmaker,
) -> bool:
    func_logger: logging.Logger = logger.getChild("populate_document_record")

    logon_token: str
    with api_backend.APILogonManager(settings_manager) as logon_token:
        # print(f"Attempting to get data providers for BO ID: {id}")
        dp_list: list[api_backend.DataProviderQueryResult] | None = api_backend.get_all_data_provider_details(
            document_id,
            settings_manager,
            logon_token
        )

    if dp_list is None or len(dp_list) == 0:
        return False

    with session_maker() as session:
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

    return True
