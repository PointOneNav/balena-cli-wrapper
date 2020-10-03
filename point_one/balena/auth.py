import logging
import os
import re

from balena import Balena

__logger = logging.getLogger("point_one.balena.auth")


def get_auth_token():
    auth_token = os.environ.get("BALENA_AUTH_TOKEN", None)

    if auth_token is None:
        token_file = os.path.expanduser("~/.balena/token")
        config_file = os.path.expanduser("~/.balena/balena.cfg")

        if os.path.exists(token_file):
            __logger.debug("Reading auth token from '%s'." % token_file)
            with open(token_file, "r") as f:
                auth_token = f.read().strip()
                if auth_token == "":
                    raise ValueError("Auth token file empty (%s)." % token_file)
        elif os.path.exists(config_file):
            __logger.debug("Reading auth token from '%s'." % config_file)
            with open(config_file, "r") as f:
                for line in f.readline():
                    m = re.match(r"token = (.*)", line)
                    if m:
                        auth_token = m.group(1)
                        break

                if auth_token is None:
                    raise ValueError("Auth token not found in config file (%s)." % config_file)
        else:
            raise RuntimeError("Unable to determine Balena authentication token: could not find token file or config "
                               "file.")
    else:
        __logger.debug("Using auth token from BALENA_AUTH_TOKEN environment variable.")

    return auth_token


def authenticate(auth_token=None):
    if auth_token is None:
        auth_token = get_auth_token()

    balena = Balena()
    balena.auth.login_with_token(auth_token)
    return balena
