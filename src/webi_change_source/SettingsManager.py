import tomllib
from pathlib import Path
from random import shuffle


class SettingsManager:
    def __init__(
        self,
        settings_file_path: Path,
    ):
        with open(settings_file_path, "rb") as f:
            raw_settings: dict = tomllib.load(f)

        self.cms_server_host: str = raw_settings["settings"]["cms_server_host"]
        self.cms_server_port: int = raw_settings["settings"]["cms_server_port"]
        self.username: str = raw_settings["settings"]["username"]
        self.password: str = raw_settings["settings"]["password"]
        self.auth_type: str = raw_settings["settings"]["auth_type"]
        self.old_universe_id: int = raw_settings["settings"]["old_universe_id"]
        self.new_universe_id: int = raw_settings["settings"]["new_universe_id"]
        self.webi_document_list_file_path: Path = Path(raw_settings["settings"]["webi_document_list_file_path"])
        self.update_document_data: bool = raw_settings["settings"]["update_document_data"]
        self.perform_change_source: bool = raw_settings["settings"]["perform_change_source"]
        self.num_workers: bool = raw_settings["settings"]["num_workers"]
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
