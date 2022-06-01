import os
import sys
import logging
from logging import StreamHandler, Formatter
from typing import List
from app.entities import (
    DebugData,
    TestsData,
    TestingData,
    DeleteData,
    CreateData,
    StatusData,
    StatusAllData
)

import psycopg2
from app import config
from app.service import exceptions
from app.service import messages
from app.service.enums import SQLCommandType

logger = logging.getLogger('logger')
logger.setLevel(logging.DEBUG if config.DEBUG else logging.ERROR)
handler = StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
handler.setFormatter(
    Formatter(fmt='[%(asctime)s: %(levelname)s] %(message)s')
)


class PostgresqlService:

    @classmethod
    def status(cls, name) -> StatusData:
        """
        name: str, database name that's being checked
        data.name = name
        data.status: str, status of the checked database 'active'/'not_exists'
        """
        data = StatusData
        with psycopg2.connect(
            host=config.PSQL_HOST,
            user=config.PSQL_USER,
            password=config.PSQL_PASSWORD,
            port=config.PSQL_PORT
        ) as con:
            try:
                with con.cursor() as cursor:
                    cursor.execute(
                        "SELECT datname "
                        "FROM pg_database "
                        f"WHERE datname = '{data.name}';"
                    )
                    result = len(cursor.fetchall())
                    data.status = 'active' if result > 0 else 'not exists'
            except Exception as e:
                raise exceptions.ServiceException(
                    message=messages.MSG_1,
                    details=str(e)
                )
            else:
                return data

    @classmethod
    def status_all(cls) -> StatusAllData:
        """
        returns a list of all databases on the server and their status 'active'/'not exists'
        """
        data = StatusAllData()
        data.status = []
        data.name = []

        with psycopg2.connect(
            host=config.PSQL_HOST,
            user=config.PSQL_USER,
            password=config.PSQL_PASSWORD,
            port=config.PSQL_PORT
        ) as con:
            with con.cursor() as cursor:
                sqlCreateDatabase = "SELECT datname FROM pg_database ;"
                try:
                    cursor.execute(sqlCreateDatabase)
                    result = cursor.fetchall()
                except Exception as e:
                    raise exceptions.ServiceException(
                        message=messages.MSG_1,
                        details=str(e)
                    )
                else:
                    for name in result:
                        stat = cls.status(str(name[0]))
                        data.status.append(stat.status)
                        data.name.append(stat.name)
        return data

    @classmethod
    def create(cls, data: CreateData) -> CreateData:
        """
        (re)create db from file
        data.filename: database dump file from directory /app/backup (db.sql, db.dump)
        returns state of the database, 'active' - successfully created, 'not exists' - error occurred
        """
        file_path = f'{config.PSQL_BACKUP_DIR}/{data.filename}'
        pwd = config.PSQL_PASSWORD
        usr = config.PSQL_USER
        prt = config.PSQL_PORT
        host = config.PSQL_HOST
        name = data.name
        cmnd = (
            f'export PGPASSWORD={pwd} && '
            f'dropdb -f --if-exists -U {usr} -h {host} -p {prt} {name} && '
            f'createdb -U {usr} -h {host} -p {prt} {name} && '
            f'psql -U {usr} -h {host} -p {prt} {name} < {file_path} '
        )
        logger.debug(cmnd)
        try:
            os.system(cmnd)
        except Exception as e:
            raise exceptions.ServiceException(
                message=messages.MSG_1,
                details=str(e)
            )
        else:
            data.status = 'active'
        return data

    @classmethod
    def delete(cls, data: DeleteData):
        """
        drops selected database
        data.name: str, name of a database that's being dropped
        returns status of the database 'active' - error occurred,
        'not exists' - success
        """
        con = psycopg2.connect(
            host=config.PSQL_HOST,
            user=config.PSQL_USER,
            password=config.PSQL_PASSWORD,
            port=config.PSQL_PORT
        )
        con.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
        )
        cursor = con.cursor()
        try:
            cursor.execute(f"drop database {data.name};")
        except Exception as e:
            raise exceptions.ServiceException(
                message=messages.MSG_1,
                details=str(e)
            )
        finally:
            con.close()

    @classmethod
    def _select_from_db(
        cls,
        db_name: str,
        student_command: str,
        true_command: str
    ) -> List[tuple]:
        """
        execute select query
        db_name - database for the query
        student_command - query sent by the user
        true_command - command that successfully solves the task
        """

        sql = f"""
        SELECT 
            CASE 
            WHEN NOT EXISTS (
              ({student_command})
              EXCEPT 
              ({true_command})
            ) THEN TRUE
            ELSE FALSE
          END;"""
        with psycopg2.connect(
            host=config.PSQL_HOST,
            user=config.PSQL_USER,
            database=db_name,
            password=config.PSQL_PASSWORD,
            port=config.PSQL_PORT
        ) as con:
            with con.cursor() as cursor:
                try:
                    cursor.execute(sql)
                    result = cursor.fetchall()
                except Exception as e:
                    logger.error(e)
                    logger.error(sql)
                    raise exceptions.ServiceException(
                        message=messages.MSG_1,
                        details=str(e)
                    )
                finally:
                    con.rollback()

        return result

    @classmethod
    def _change_db(
        cls,
        db_name: str,
        student_command: str,
        check_command: str
    ) -> List[tuple]:
        """
        execute query DELTE/UPDATE/INSERT
        db_name - database for the query
        student_command - query sent by the user
        true_command - command that checks changed database
        """
        with psycopg2.connect(
            host=config.PSQL_HOST,
            user=config.PSQL_USER,
            database=db_name,
            password=config.PSQL_PASSWORD,
            port=config.PSQL_PORT
        ) as con:
            with con.cursor() as cursor:
                try:
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
                    result = cursor.fetchall()
                except Exception as e:
                    logger.error(e)
                    raise exceptions.ServiceException(
                        message=messages.MSG_1,
                        details=str(e)
                    )
                finally:
                    con.rollback()
        return result

    @classmethod
    def debug(cls, data: DebugData) -> DebugData:
        """
        debug query
        data.request_typ: 'select'/'something else', meaning DELETE/UPDATE/INSERT
        returns list of bools, corresponding to success or failure of a test
        """
        with psycopg2.connect(
            host=config.PSQL_HOST,
            user=config.PSQL_USER,
            database=data.name,
            password=config.PSQL_PASSWORD,
            port=config.PSQL_PORT
        ) as con:
            with con.cursor() as cursor:
                try:
                    cursor.execute(data.code)
                    if cursor.description:
                        data.result = cursor.fetchall()
                except Exception as e:
                    logger.error(e)
                    raise exceptions.ExecutionException(details=str(e))
                else:
                    return data
                finally:
                    con.rollback()

    @classmethod
    def _test(
        cls,
        data: TestsData,
        name: str,
        code: str,
        check_code: str,
        request_type: SQLCommandType
    ) -> TestsData:
        """
        runs a test during testing
        name: str, query database
        code: str, user's query
        check_code: str, code for checking the query result
        request_type: type of a query - 'select' / 'something else' , meaning DELETE/UPDATE/INSERT
        returns bool result of the query - success/failure
        """
        if request_type == SQLCommandType.SELECT:
            result = cls._select_from_db(name, code, check_code)
        else:
            result = cls._change_db(name, code, check_code)
        for row in result:
            for col in row:
                if col is True:
                    data.ok = True
        return data

    @classmethod
    def testing(cls, data: TestingData) -> TestingData:
        """
        runs _test for all items in data.tests (TestsData)
        returns results of running all tests
        """
        for test in data.tests:
            result = cls._test(
                data=test,
                name=data.name,
                code=data.code,
                check_code=test.data_in,
                request_type=data.request_type
            )
            test.ok = result.ok
            test.error = result.error
        return data
