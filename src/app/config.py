from os import (
    environ as env,
    getuid,
    path
)
from tempfile import gettempdir

TMP_DIR = gettempdir()
TIMEOUT = 5  # seconds

SANDBOX_USER_UID = int(env.get('SANDBOX_USER_UID', getuid()))

# needs to be set up manually
PSQL_USER = "ps_user"
PSQL_PASSWORD = "ps_user"
PSQL_PORT = "5433"
PSQL_HOST = "postgresmodule-db"

APP_PATH = path.dirname(path.dirname(path.dirname(__file__)))
