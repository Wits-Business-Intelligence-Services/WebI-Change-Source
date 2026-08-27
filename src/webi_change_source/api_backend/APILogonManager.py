import logging
from contextlib import contextmanager

from .api_functions import __login, __logoff

logger: logging.Logger = logging.getLogger(__name__)


@contextmanager
def APILogonManager(
    settings_manager,
):
    class_logger: logging.Logger = logger.getChild("APILogonManager")
    logon_token: str = ""
    try:
        logon_token = __login(settings_manager)
        yield logon_token

    finally:
        class_logger.info(f"Logging off with token: {logon_token}")
        __logoff(settings_manager, logon_token)
