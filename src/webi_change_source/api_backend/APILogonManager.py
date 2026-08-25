import logging
from contextlib import contextmanager

from .api_functions import __login, __logoff


@contextmanager
def APILogonManager(settings_manager, logger: logging.Logger):
    logon_token: str = ""
    try:
        logon_token = __login(settings_manager, logger)
        yield logon_token

    finally:
        __logoff(settings_manager, logon_token, logger)
