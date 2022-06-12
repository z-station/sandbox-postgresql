from os import environ as env
from psycopg2.extras import LoggingConnection
from psycopg2.extensions import connection


DEBUG = env.get('DEBUG', 'false') == 'true'

PSQL_USER = env.get('PSQL_USER', 'sandbox')
PSQL_PASSWORD = env.get('PSQL_PASSWORD', 'sandbox')
PSQL_PORT = env.get('PSQL_PORT', 5433)
PSQL_HOST = env.get('PSQL_HOST', 'localhost')
PSQL_CONFIG = {
    'user': PSQL_USER,
    'password': PSQL_PASSWORD,
    'port': PSQL_PORT,
    'host': PSQL_HOST,
    'connection_factory': LoggingConnection if DEBUG else connection
}

# Директория внутри контейнера с приложением
# где хранятся .sql файлы создаваемых баз
SQL_FILES_DIR = '/files'
