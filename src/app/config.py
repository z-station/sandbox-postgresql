from os import (
    environ as env,
    getuid,
    path
)
from tempfile import gettempdir

TMP_DIR = gettempdir()
TIMEOUT = 5  # seconds

SANDBOX_USER_UID = int(env.get('SANDBOX_USER_UID', getuid()))

PSQL_USER = env.get('PSQL_USER', 'sandbox')
PSQL_PASSWORD = env.get('PSQL_PASSWORD', 'sandbox')
PSQL_PORT = env.get('PSQL_PORT', 5433)
PSQL_HOST = env.get('PSQL_HOST', 'localhost')
PSQL_BACKUP_DIR = '/files/backup'

DEBUG = env.get('DEBUG', 'true') == 'true'
