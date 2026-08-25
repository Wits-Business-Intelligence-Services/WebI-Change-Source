import logging
from json import JSONDecoder

from requests import Response, get, post, put

from webi_change_source.SettingsManager import SettingsManager
from .DataProviderQueryResult import DataProviderQueryResult


def __extract_response(
        response: Response, logger: logging.Logger
) -> tuple[bool, dict | None, str | None]:
    logger.info(f"response.ok: {response.ok!r}")
    decoded_response_dict: dict = JSONDecoder().decode(response.text)
    logger.info(f"decoded_response_dict: {decoded_response_dict!r}")

    return (
        response.ok,
        JSONDecoder().decode(response.text) if response.ok else None,
        response.text if response.ok else None,
    )


def __login(
        settings_manager: SettingsManager, logger: logging.Logger
) -> str:
    body: dict = {
        "userName": settings_manager.username,
        "password": settings_manager.password,
        "auth": settings_manager.auth_type,
    }

    ok, response_dict, _ = __extract_response(
        post(
            url=f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/logon/long",
            json=body,
            headers=settings_manager.standard_headers,
        ),
        logger,
    )

    if not ok or response_dict is None:
        raise ConnectionError("Invalid logon")

    return response_dict["logonToken"]


def __logoff(
        settings_manager: SettingsManager,
        logon_token: str,
        logger: logging.Logger
) -> bool:
    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    response: Response = post(
        url=f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/logoff",
        headers=headers,
    )

    return response.ok


def get_document_details(
        document_id: int,
        settings_manager: SettingsManager,
        logon_token: str,
        logger: logging.Logger
) -> dict | None:
    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    url: str = f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/raylight/v1/documents/{document_id}"

    ok, response_dict, _ = __extract_response(get(url=url, headers=headers), logger)

    return response_dict["document"] if ok and response_dict is not None else None


def get_all_data_provider_details(
        document_id: int,
        settings_manager: SettingsManager,
        logon_token: str,
        logger: logging.Logger
) -> list[DataProviderQueryResult] | None:
    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    url: str = f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/raylight/v1/documents/{document_id}/dataproviders"

    ok, response_dict, _ = __extract_response(get(url=url, headers=headers), logger)

    processed_dps: list[DataProviderQueryResult] | None = None

    if ok and response_dict is not None:
        dps: list[dict] = response_dict["dataproviders"]["dataprovider"]
        processed_dps = [
            DataProviderQueryResult(
                data_source_id=x["dataSourceId"] if "dataSourceId" in x else 0,
                data_source_type=x["dataSourceType"] if "dataSourceType" in x else "UNK",
                id=x["id"] if "id" in x else "UNK",
                name=x["name"] if "name" in x else "UNK",
            )
            for x in dps
        ]

    return processed_dps if ok else None


def get_data_provider_mappings(
        document_id: int,
        id_dp: str,
        settings_manager: SettingsManager,
        logon_token: str,
        logger: logging.Logger
) -> tuple[list | None, str | None]:
    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    body: dict = {
        "policy": {"qualificationTolerance": "High", "dataTypeTolerance": "High"},
        "strategies": [{"strategy": [{"@name": "SameId"}]}],
    }

    url: str = f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/raylight/v1/documents/{document_id}/dataproviders/mappings"

    params: dict = {
        "originDataproviderIds": id_dp,
        "targetDatasourceId": settings_manager.new_universe_id,
    }

    ok, response_dict, response_text = __extract_response(
        get(url=url, headers=headers, data=body, params=params), logger
    )

    return response_dict["mappings"]["content"][
        "mapping"
    ] if ok and response_dict is not None else None, response_text if ok else None


def change_data_provider_mappings(
        document_id: int,
        dp_id: str,
        mappings: str,
        settings_manager: SettingsManager,
        logon_token: str,
        logger: logging.Logger
) -> tuple[bool, dict | None, str | None]:
    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    url: str = f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/raylight/v1/documents/{document_id}/dataproviders/mappings"

    params: dict = {
        "originDataproviderIds": dp_id,
        "targetDatasourceId": settings_manager.new_universe_id,
        "skipChecking": "true",
    }

    ok, response_dict, response_text = __extract_response(
        post(url=url, headers=headers, data=mappings, params=params), logger
    )

    ok = ok and response_dict is not None and 'has not been modified' not in \
         response_dict['success']['message']

    return ok, response_dict, response_text


def save_changes_to_document(
        document_id: int,
        settings_manager: SettingsManager,
        logon_token: str,
        logger: logging.Logger
) -> bool:
    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    url: str = f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/raylight/v1/documents/{document_id}"

    ok, response_dict, response_text = __extract_response(
        put(url=url, headers=headers), logger
    )

    return ok


def set_document_unused(
        document_id: int,
        settings_manager: SettingsManager,
        logon_token: str,
        logger: logging.Logger
) -> bool:
    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    body: dict = {"document": {"state": "Unused"}}

    url: str = f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/raylight/v1/documents/{document_id}"

    ok, response_dict, response_text = __extract_response(
        put(url=url, headers=headers, json=body), logger
    )

    return ok
