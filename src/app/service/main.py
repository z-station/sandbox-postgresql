import os
import psycopg2
from typing import Optional, Tuple
from tabulate import tabulate
from psycopg2.extensions import (
    AsIs,
    ISOLATION_LEVEL_AUTOCOMMIT,
)
from typing import List
from app.entities import (
    DebugData,
    TestData,
    TestingData,
    StatusData,
)
from app import config
from app.service import exceptions
from app.service.enums import (
    SQLCommandType,
    DbStatus,
    DebugFormat,
)
from app.logger import get_logger
logger = get_logger()


class PostgresqlService:

    db_name_prefix = 'sandbox_'

    @classmethod
    def _get_db_name(cls, name: str) -> str:
        return f'{cls.db_name_prefix}{name}'

    @classmethod
    def _delete_database(cls, name: str):
        con = None
        try:
            con = psycopg2.connect(**config.PSQL_CONFIG)
            if config.DEBUG:
                con.initialize(logger)
            con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = con.cursor()
            cursor.execute(
                'DROP DATABASE IF EXISTS %(db_name)s WITH (FORCE)',
                {'db_name': AsIs(cls._get_db_name(name))}
            )
        except Exception as e:
            logger.error(e)
            raise exceptions.DeletionException(details=str(e))
        finally:
            if con:
                con.close()

    @classmethod
    def _create_database(cls, name: str):
        con = None
        try:
            con = psycopg2.connect(**config.PSQL_CONFIG)
            if config.DEBUG:
                con.initialize(logger)
            con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = con.cursor()
            cursor.execute(
                'CREATE DATABASE %(db_name)s '
                'WITH OWNER = %(user)s',
                {
                    'db_name': AsIs(cls._get_db_name(name)),
                    'user': AsIs(config.PSQL_USER)
                }
            )
        except Exception as e:
            logger.error(e)
            raise exceptions.CreationException(details=str(e))
        finally:
            if con:
                con.close()

    @classmethod
    def _load_database_from_file(cls, name: str, filename: str):

        file_path = f'{config.SQL_FILES_DIR}/{filename}'
        if not os.path.exists(file_path):
            raise exceptions.FileNotFound()
        command = (
            f'export PGPASSWORD={config.PSQL_PASSWORD} && '
            f'psql -U {config.PSQL_USER} '
            f'-h {config.PSQL_HOST} '
            f'-p {config.PSQL_PORT} '
            f'{cls._get_db_name(name)} < {file_path}'
        )
        logger.debug(command)
        try:
            os.system(command)
        except Exception as e:
            logger.error(e)
            raise exceptions.CreationException(details=str(e))

    @classmethod
    def _check_select_command(
        cls,
        name: str,
        student_command: str,
        true_command: str
    ) -> bool:

        """
        execute select query
        name - database for the query
        student_command - query sent by the user
        true_command - command that successfully solves the task

        return True if select rows by student_command identical rows
        from the true_command.

        Example:
            student_command: SELECT title FROM tasks_task LIMIT 10
            true_command: SELECT title FROM tasks_task LIMIT 10 OFFSET 0
        """

        try:
            with psycopg2.connect(
                **config.PSQL_CONFIG,
                database=cls._get_db_name(name)
            ) as con:
                if config.DEBUG:
                    con.initialize(logger)
                with con.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT 
                          CASE 
                            WHEN NOT EXISTS (
                              ({student_command})
                              EXCEPT 
                              ({true_command})
                            ) THEN TRUE
                            ELSE FALSE
                          END
                    """)
                    result = cursor.fetchone()
                con.rollback()
        except psycopg2.errors.SyntaxError as e:
            if 'each EXCEPT query must have the same number of columns' in str(e):
                raise exceptions.CheckException()
            raise
        return result[0]

    @classmethod
    def _check_delete_command(
        cls,
        name: str,
        student_command: str,
        check_command: str
    ) -> bool:
        """
        execute query DELETE
        name - database for the query
        student_command - query sent by the user
        true_command - command that checks changed database
        return True if deleted row not exist in result.

        Example:
            student_command: DELETE FROM tasks_task WHERE id IN (25, 35)
            check_command: SELECT title FROM tasks_task WHERE id IN (25, 35)
        """

        with psycopg2.connect(
            **config.PSQL_CONFIG,
            database=cls._get_db_name(name)
        ) as con:
            if config.DEBUG:
                con.initialize(logger)
            with con.cursor() as cursor:
                cursor.execute(student_command)
                cursor.execute(f"""
                    SELECT 
                      CASE 
                        WHEN NOT EXISTS (
                          {check_command}
                        ) THEN TRUE
                        ELSE FALSE
                      END 
                """)
                result = cursor.fetchone()
            con.rollback()
        return result[0]

    @classmethod
    def _check_update_or_insert_command(
        cls,
        name: str,
        student_command: str,
        check_code: str
    ) -> bool:
        """
        execute query UPDATE/INSERT
        name - database for the query
        student_command - query sent by the user
        check_command - select command that checks changed database
          (1st line is amount of objects returned)
        return True if count rows from db equal check_command count

          Example check_command for UPDATE:
            student_command:
                UPDATE tasks_task SET title='test' WHERE id=50
            check_code:
                1
                SELECT title FROM tasks_task WHERE id=50 AND title='test

          Example check_command for INSERT:
            student_command:
                INSERT INTO tasks_task (title, lang) VALUES ('test', 'psql')
            check_code:
                1
                SELECT title
                FROM tasks_task
                WHERE title='test' AND lang = 'psql'
        """
        with psycopg2.connect(
            **config.PSQL_CONFIG,
            database=cls._get_db_name(name)
        ) as con:
            if config.DEBUG:
                con.initialize(logger)
            with con.cursor() as cursor:
                try:
                    expected_rows_count = int(check_code.split("\n", 1)[0])
                    check_command = check_code.split("\n", 1)[1]
                except Exception as e:
                    raise exceptions.InvalidCheckCommand(details=str(e))
                else:
                    cursor.execute(student_command)
                    cursor.execute(
                        'SELECT COUNT(*) '
                        f'FROM ({check_command}) AS check_result'
                    )
                    rows_count = cursor.fetchone()[0]
                    con.rollback()
                    return rows_count == expected_rows_count

    @classmethod
    def _test(
        cls,
        check_code: str,
        name: str,
        code: str,
        request_type: SQLCommandType
    ) -> Tuple[bool, Optional[str]]:
        """
        runs a test during testing
        name: str, query database
        code: str, user's query
        check_code: str, code for checking the query result
        request_type: type of a query SELECT/DELETE/UPDATE/INSERT
        returns two values: ok and error message """

        ok, error = False, None
        try:
            if request_type == SQLCommandType.SELECT:
                ok = cls._check_select_command(
                    name=name,
                    student_command=code,
                    true_command=check_code
                )
            elif request_type == SQLCommandType.DELETE:
                ok = cls._check_delete_command(
                    name=name,
                    student_command=code,
                    check_command=check_code
                )
            else:
                ok = cls._check_update_or_insert_command(
                    name=name,
                    student_command=code,
                    check_code=check_code
                )
        except Exception as e:
            logger.error(e)
            ok = False
            error = str(e)
        return ok, error

    @classmethod
    def status(cls, name: str) -> StatusData:

        """ Returns the status of the database with the given name """

        data = StatusData(
            status=DbStatus.NOT_EXISTS,
            name=name
        )
        try:
            with psycopg2.connect(**config.PSQL_CONFIG) as con:
                if config.DEBUG:
                    con.initialize(logger)
                with con.cursor() as cursor:
                    cursor.execute(
                        'SELECT datname '
                        'FROM pg_database '
                        'WHERE datname = %(db_name)s',
                        {'db_name': cls._get_db_name(name)}
                    )
                    if cursor.fetchone():
                        data.status = DbStatus.ACTIVE
        except Exception as e:
            logger.error(e)
            raise exceptions.StatusCheckException(details=str(e))
        return data

    @classmethod
    def status_all(cls) -> List[StatusData]:

        """ Returns a list for all sandbox databases with their statuses """

        data = []
        try:
            with psycopg2.connect(**config.PSQL_CONFIG) as con:
                if config.DEBUG:
                    con.initialize(logger)
                with con.cursor() as cursor:
                    cursor.execute(
                        'SELECT split_part(datname, %(db_name_prefix)s, 2) ' 
                        'FROM pg_database '
                        'WHERE datname LIKE %(db_name_prefix_template)s',
                        {
                            'db_name_prefix': cls.db_name_prefix,
                            'db_name_prefix_template': f'{cls.db_name_prefix}%'
                        }
                    )
                    result = cursor.fetchall()
        except Exception as e:
            logger.error(e)
            raise exceptions.StatusCheckException(details=str(e))
        else:
            for row in result:
                data.append(
                    StatusData(
                        name=row[0],
                        status=DbStatus.ACTIVE
                    )
                )
            return data

    @classmethod
    def create(cls, name: str, filename: str):
        """
        (Re)creates db from file
        data.filename: database dump file from directory /files
        Returns state of the database, 'active' - successfully created,
        'not exists' - error occurred
        """

        cls._delete_database(name)
        cls._create_database(name)
        cls._load_database_from_file(name=name, filename=filename)

    @classmethod
    def delete(cls, name: str):

        """ Delete the database with the given name """

        cls._delete_database(name)

    @classmethod
    def debug(cls, data: DebugData) -> DebugData:
        """
        debug query
        data.request_typ: 'select'/'something else', meaning DELETE/UPDATE/INSERT
        returns list of bools, corresponding to success or failure of a test
        """
        result = []
        column_names = None
        try:
            with psycopg2.connect(
                **config.PSQL_CONFIG,
                database=cls._get_db_name(data.name)
            ) as con:
                if config.DEBUG:
                    con.initialize(logger)
                with con.cursor() as cursor:
                    cursor.execute(data.code)
                    if cursor.description:
                        column_names = [desc[0] for desc in cursor.description]
                        if data.format == DebugFormat.ARRAY:
                            result.append(column_names)
                        for row in cursor.fetchall():
                            result.append(row)
                con.rollback()
        except Exception as e:
            data.error = str(e)
        else:
            if data.format == DebugFormat.TABULAR:
                data.result = tabulate(
                    tabular_data=result,
                    headers=column_names,
                    tablefmt="psql"
                )
            else:
                data.result = result
        return data

    @classmethod
    def testing(cls, data: TestingData) -> TestingData:
        """
        runs _test for all items in data.tests (TestData)
        returns results of running all tests
        """
        for test_data in data.tests:
            test_data.ok, test_data.error = cls._test(
                check_code=test_data.data_in,
                name=data.name,
                code=data.code,
                request_type=data.request_type
            )
        return data
