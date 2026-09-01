import tomllib
from pathlib import Path
from random import shuffle


class SettingsManager:
    def __init__(
        self,
        settings_file_path: Path,
        webi_document_list_path: str,
        update_document_data: bool,
        perform_change_source: bool,
        num_workers: int
    ):
        with open(settings_file_path, "rb") as f:
            raw_settings: dict = tomllib.load(f)

        self.cms_server_host: str = raw_settings["settings"]["cms_server_host"]
        self.cms_server_port: int = raw_settings["settings"]["cms_server_port"]
        self.username: str = raw_settings["settings"]["username"]
        self.password: str = raw_settings["settings"]["password"]
        self.auth_type: str = raw_settings["settings"]["auth_type"]
        self.source_universe_id: int = raw_settings["settings"]["source_universe_id"]
        self.target_universe_id: int = raw_settings["settings"]["target_universe_id"]
        self.webi_document_list_file_path: Path = Path(webi_document_list_path)
        self.update_document_data: bool = update_document_data
        self.perform_change_source: bool = perform_change_source
        self.num_workers: int = num_workers
        with open(self.webi_document_list_file_path, "r") as f:
            self.document_list: list[int] = [int(x.strip()) for x in f if x != ""]
            shuffle(self.document_list)

    @property
    def standard_headers(
        self,
    ) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
