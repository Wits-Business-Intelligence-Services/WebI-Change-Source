import logging
from json import JSONDecoder

from requests import Response, get, post, put

from webi_change_source.SettingsManager import SettingsManager
from .DataProviderQueryResult import DataProviderQueryResult

logger: logging.Logger = logging.getLogger(__name__)


def __extract_response(
    response: Response,
    func_logger: logging.Logger,
) -> tuple[bool, dict | None, str | None]:
    extract_logger: logging.Logger = func_logger.getChild("__extract_response")

    decoded_response_dict: dict = JSONDecoder().decode(response.text)

    extract_logger.debug(f"response.ok: {response.ok!r}")
    extract_logger.debug(f"decoded_response_dict: {decoded_response_dict!r}")

    return (
        response.ok,
        JSONDecoder().decode(response.text) if response.ok else None,
        response.text if response.ok else None,
    )


def __login(
    settings_manager: SettingsManager,
) -> str:
    func_logger: logging.Logger = logger.getChild("__login")

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
        func_logger,
    )

    if not ok or response_dict is None:
        func_logger.critical("Failed to log in")
        raise ConnectionError("Invalid logon")

    func_logger.info("Successfully logged in")

    return response_dict["logonToken"]


def __logoff(
    settings_manager: SettingsManager,
    logon_token: str,
) -> bool:
    func_logger: logging.Logger = logger.getChild("__logoff")

    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    response: Response = post(
        url=f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/logoff",
        headers=headers,
    )
    func_logger.debug(f"Logoff successful for {logon_token}")

    return response.ok


def get_document_details(
    document_id: int,
    settings_manager: SettingsManager,
    logon_token: str,
) -> dict | None:
    func_logger: logging.Logger = logger.getChild("get_document_details")

    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    url: str = f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/raylight/v1/documents/{document_id}"

    ok: bool
    response_dict: dict | None
    ok, response_dict, _ = __extract_response(
        get(url=url, headers=headers),
        func_logger
    )

    if ok and response_dict is not None:
        func_logger.info(f"Successfully got document details for {document_id}")
    else:
        func_logger.error(f"Failed to get document details for {document_id}")

    return response_dict["document"] if ok and response_dict is not None else None


def get_single_data_provider_details(
    document_id: int,
    data_provider_id: str,
    settings_manager: SettingsManager,
    logon_token: str,
) -> DataProviderQueryResult | None:
    func_logger: logging.Logger = logger.getChild("get_single_data_provider_details")

    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    url: str = f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/raylight/v1/documents/{document_id}/dataproviders/{data_provider_id}"

    ok: bool
    response_dict: dict | None
    ok, response_dict, _ = __extract_response(
        get(url=url, headers=headers),
        func_logger
    )

    if ok and response_dict is not None:
        dp_record: dict = response_dict["dataprovider"]
        dp = DataProviderQueryResult(
            data_source_id=dp_record["dataSourceId"] if "dataSourceId" in dp_record else -1,
            data_source_type=dp_record["dataSourceType"] if "dataSourceType" in dp_record else "UNKNOWN",
            id=dp_record["id"] if "id" in dp_record else "UNKNOWN",
            name=dp_record["name"] if "name" in dp_record else "UNKNOWN",
        )

        func_logger.info(f"Successfully got data provider details for {document_id}:{data_provider_id}")
        return dp
    else:
        func_logger.error(f"Failed to get data provider details for {document_id}:{data_provider_id}")
        return None


def get_all_data_provider_details(
    document_id: int,
    settings_manager: SettingsManager,
    logon_token: str,
) -> list[DataProviderQueryResult] | None:
    func_logger: logging.Logger = logger.getChild("get_all_data_provider_details")

    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    url: str = f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/raylight/v1/documents/{document_id}/dataproviders"

    ok: bool
    response_dict: dict | None
    ok, response_dict, _ = __extract_response(
        get(url=url, headers=headers),
        func_logger
    )

    processed_dps: list[DataProviderQueryResult] | None = None

    if ok and response_dict is not None:
        dps: list[dict] = response_dict["dataproviders"]["dataprovider"]

        processed_dps = []

        for dp in dps:
            dp_add_status: bool = False
            if "id" in dp:
                dp_result: DataProviderQueryResult | None = get_single_data_provider_details(
                    document_id, dp["id"], settings_manager, logon_token)
                if dp_result is not None:
                    processed_dps.append(dp_result)
                    dp_add_status = True

            if not dp_add_status:
                processed_dps.append(
                    DataProviderQueryResult(
                        data_source_id=-1,
                        data_source_type="UNKNOWN",
                        id="UNKNOWN",
                        name="UNKNOWN",
                    )
                )

        func_logger.info(f"Successfully got all data provider details for {document_id}")
    else:
        func_logger.error(f"Failed to get all data provider details for {document_id}")

    return processed_dps if ok else None


def get_data_provider_mappings(
        document_id: int,
        id_dp: str,
        settings_manager: SettingsManager,
        logon_token: str,
) -> tuple[list | None, str | None]:
    func_logger: logging.Logger = logger.getChild("get_data_provider_mappings")

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

    ok: bool
    response_dict: dict | None
    ok, response_dict, response_text = __extract_response(
        put(url=url, headers=headers, data=body, params=params),
        func_logger
    )

    if ok and response_dict is not None:
        func_logger.info(f"Successfully retrieved mappings for data provider {document_id}:{data_provider_id}")
        return response_dict["mappings"]["content"]["mapping"], response_text
    else:
        func_logger.error(f"Failed to retrieve mappings for data provider {document_id}:{data_provider_id}")
        return None, None


def change_data_provider_mappings(
        document_id: int,
        dp_id: str,
        mappings: str,
        settings_manager: SettingsManager,
        logon_token: str,
) -> tuple[bool, dict | None, str | None]:
    func_logger: logging.Logger = logger.getChild("change_data_provider_mappings")

    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    url: str = f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/raylight/v1/documents/{document_id}/dataproviders/mappings"

    params: dict = {
        "originDataproviderIds": dp_id,
        "targetDatasourceId": settings_manager.new_universe_id,
        "skipChecking": "true",
    }

    ok: bool
    response_dict: dict | None
    ok, response_dict, response_text = __extract_response(
        post(url=url, headers=headers, data=mappings, params=params),
        func_logger
    )

    ok = ok and response_dict is not None and 'has not been modified' not in \
         response_dict['success']['message']

    return ok, response_dict, response_text
    if ok:
        func_logger.info(f"Successfully changed data provider mappings for {document_id}:{data_provider_id}")
    else:
        func_logger.error(f"Failed to change data provider mappings for {document_id}:{data_provider_id}")



def save_changes_to_document(
    document_id: int,
    settings_manager: SettingsManager,
    logon_token: str,
) -> bool:
    func_logger: logging.Logger = logger.getChild("save_changes_to_document")

    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    url: str = f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/raylight/v1/documents/{document_id}"

    ok: bool
    response_dict: dict | None
    ok, response_dict, response_text = __extract_response(
        put(url=url, headers=headers),
        func_logger
    )

    if ok:
        func_logger.info(f"Successfully saved document {document_id}")
    else:
        func_logger.error(f"Failed to save document {document_id}")

    return ok


def set_document_unused(
    document_id: int,
    settings_manager: SettingsManager,
    logon_token: str,
) -> bool:
    func_logger: logging.Logger = logger.getChild("set_document_unused")

    headers: dict = settings_manager.standard_headers
    headers["X-SAP-LogonToken"] = logon_token

    body: dict = {"document": {"state": "Unused"}}

    url: str = f"{settings_manager.cms_server_host}:{settings_manager.cms_server_port}/biprws/raylight/v1/documents/{document_id}"

    ok: bool
    response_dict: dict | None
    ok, response_dict, response_text = __extract_response(
        put(url=url, headers=headers, json=body),
        func_logger
    )

    if ok:
        func_logger.info(f"Successfully set document {document_id} to unused")
    else:
        func_logger.error(f"Failed to set document {document_id} to unused")

    return ok
