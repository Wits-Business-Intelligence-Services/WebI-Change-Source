from pathlib import Path
from .SettingsManager import SettingsManager

settings_template_path: Path = Path(__file__).parent.joinpath("settings_template.toml")

__all__ = [
    "SettingsManager",
    "settings_template_path"
]