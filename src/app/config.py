from os import (
    environ as env,
    getuid
)
from tempfile import gettempdir

TMP_DIR = gettempdir()
TIMEOUT = 5  # seconds

SANDBOX_USER_UID = int(env.get('SANDBOX_USER_UID', getuid()))



PSQL_USER = str(env.get('POSTGRES_USER'))
PSQL_PASSWORD = str(env.get('POSTGRES_PASSWORD'))
PSQL_PORT = "5433"
PSQL_HOST = "postgresmodule-db"




