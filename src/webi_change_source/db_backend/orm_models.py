from datetime import datetime

import sqlalchemy as sql
import sqlalchemy.orm as sql_orm


class Base(sql_orm.DeclarativeBase):
    type_annotation_map = {
        str: sql.TEXT,
        datetime: sql.TEXT
    }


class Document(Base):
    __tablename__ = "documents"

    id: sql_orm.Mapped[int] = sql_orm.mapped_column(primary_key=True)
    name: sql_orm.Mapped[str]
    path: sql_orm.Mapped[str]
    created_by: sql_orm.Mapped[str]
    last_author: sql_orm.Mapped[str]
    last_updated: sql_orm.Mapped[datetime]
    status: sql_orm.Mapped[str]

    def __repr__(self) -> str:
        return (f"Document("
                f"id={self.id!r}, "
                f"name={self.name!r}, "
                f"path={self.path}, "
                f"created_by={self.created_by}, "
                f"last_author={self.last_author}, "
                f"last_updated={self.last_updated!r}, "
                f")")


class DataProvider(Base):
    __tablename__ = "data_providers"

    id: sql_orm.Mapped[str] = sql_orm.mapped_column(primary_key=True)
    document_id: sql_orm.Mapped[int] = sql_orm.mapped_column(sql.ForeignKey("documents.id"), primary_key=True)
    name: sql_orm.Mapped[str]
    data_source_id: sql_orm.Mapped[int]
    data_source_original_type: sql_orm.Mapped[str]
    data_source_type: sql_orm.Mapped[str]

    def __repr__(self) -> str:
        return (f"DataProvider("
                f"id={self.id!r}, "
                f"document_id={self.document_id!r}, "
                f"name={self.name!r}, "
                f"data_source_id={self.data_source_id!r}, "
                f"data_source_original_type={self.data_source_original_type!r}, "
                f"data_source_type={self.data_source_type!r}"
                f")")


class Conversion(Base):
    __tablename__ = "conversions"

    batch_no: sql_orm.Mapped[int] = sql_orm.mapped_column(primary_key=True)
    conversion_date: sql_orm.Mapped[datetime] = sql_orm.mapped_column(primary_key=True)
    query_id: sql_orm.Mapped[str] = sql_orm.mapped_column(sql.ForeignKey("data_providers.id"), primary_key=True)
    document_id: sql_orm.Mapped[int] = sql_orm.mapped_column(sql.ForeignKey("data_providers.document_id"),
                                                             primary_key=True)

    status_dp_details: sql_orm.Mapped[str | None]
    status_dp_correct_source: sql_orm.Mapped[str | None]
    status_mappings: sql_orm.Mapped[str | None]
    status_change_source: sql_orm.Mapped[str | None]
    status_save: sql_orm.Mapped[str | None]
    status_unload: sql_orm.Mapped[str | None]

    def __repr__(self) -> str:
        return (f"DataProvider("
                f"query_id={self.query_id!r}, "
                f"document_id={self.document_id!r}, "
                f"conversion_date={self.conversion_date!r}, "
                f"status_dp_details={self.status_dp_details!r}, "
                f"status_dp_correct_source={self.status_dp_correct_source!r}, "
                f"status_mappings={self.status_mappings!r}, "
                f"status_change_source={self.status_change_source!r}, "
                f"status_save={self.status_save!r}, "
                f"status_unload={self.status_unload!r}"
                f")")
