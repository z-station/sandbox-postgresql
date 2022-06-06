import os
import sys
from tabulate import tabulate
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
        try:
            with psycopg2.connect(
                host=config.PSQL_HOST,
                user=config.PSQL_USER,
                password=config.PSQL_PASSWORD,
                port=config.PSQL_PORT
            ) as con:
                with con.cursor() as cursor:
                    cursor.execute(
                        "SELECT datname "
                        "FROM pg_database "
                        f"WHERE datname = '{name}';"
                    )
                    result = len(cursor.fetchall())
                    data.status = 'active' if result > 0 and "sandbox_database" in name else 'not exists'
                    data.name = name
        except Exception as e:
            raise exceptions.StatusCheckException(
                message=messages.MSG_3,
                details=str(e)
            )
        return data

    @classmethod
    def status_all(cls) -> StatusAllData:
        """
        returns a list of all databases on the server and their status 'active'/'not exists'
        """
        data = StatusAllData()
        data.status = []
        data.name = []
        try:
            with psycopg2.connect(
                host=config.PSQL_HOST,
                user=config.PSQL_USER,
                password=config.PSQL_PASSWORD,
                port=config.PSQL_PORT
            ) as con:
                with con.cursor() as cursor:
                    sqlCreateDatabase = "SELECT datname FROM pg_database ;"
                    cursor.execute(sqlCreateDatabase)
                    result = cursor.fetchall()
        except Exception as e:
            raise exceptions.StatusCheckException(
                message=messages.MSG_3,
                details=str(e)
            )
        else:
            for name in result:
                stat = cls.status(str(name[0]))
                if "sandbox_database" in str(name[0]):
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
        fp1 = os.path.join(config.APP_PATH, config.PSQL_BACKUP_DIR)
        file_path = f'{fp1}/{data.filename}'

        try:
            db_exists = os.path.exists(file_path)
            if not db_exists:
                raise Exception("no such database file")

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
            os.system(cmnd)
            data.status = 'active'
        except Exception as e:
            data.message = messages.MSG_1,
            data.details = str(e)
            data.status = 'doesnt exist'

        return data

    @classmethod
    def delete(cls, data: DeleteData) -> DeleteData:
        """
        drops selected database
        data.name: str, name of a database that's being dropped
        returns status of the database 'active' - error occurred,
        'not exists' - success
        """
        try:
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
            cursor.execute(f"drop database \"" + data.name + "\" ;")
            con.close()
        except Exception as e:
            data.message = messages.MSG_2
            data.details = str(e)

        return data

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
                cursor.execute(sql)
                result = cursor.fetchall()
            con.rollback()
        return result

    @classmethod
    def _delete_from_db(
        cls,
        db_name: str,
        student_command: str,
        check_command: str
    ) -> List[tuple]:
        """
        execute query DELTE
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
            con.rollback()

        return result


    @classmethod
    def _update_or_insert_into_db(
        cls,
        db_name: str,
        student_command: str,
        check_command: str
    ) -> List[tuple]:
        """
        execute query UPDATE/INSERT
        db_name - database for the query
        student_command - query sent by the user
        true_command - select command that checks changed database (1st line is amount of objects returned)
        """
        with psycopg2.connect(
            host=config.PSQL_HOST,
            user=config.PSQL_USER,
            database=db_name,
            password=config.PSQL_PASSWORD,
            port=config.PSQL_PORT
        ) as con:
            with con.cursor() as cursor:
                cursor.execute(student_command)
                cnt_output = int(check_command.split("\n", 1)[0])
                check_command = check_command.split("\n", 1)[1]
                cursor.execute(f"""
                                SELECT COUNT(*) FROM (
                                        {check_command}) as FOO
                            ;""")
                result = int(cursor.fetchall()[0][0])
                logger.info(str(result))
                logger.info(str(cnt_output))
                if result == cnt_output:
                    result = [(True,)]
                else:
                    result = [(False,)]
            con.rollback()

        return result


    @classmethod
    def debug(cls, data: DebugData) -> DebugData:
        """
        debug query
        data.request_typ: 'select'/'something else', meaning DELETE/UPDATE/INSERT
        returns list of bools, corresponding to success or failure of a test
        """
        try:
            with psycopg2.connect(
                host=config.PSQL_HOST,
                user=config.PSQL_USER,
                database=data.name,
                password=config.PSQL_PASSWORD,
                port=config.PSQL_PORT
            ) as con:
                with con.cursor() as cursor:
                    cursor.execute(data.code)
                    if cursor.description:
                        result = [desc[0] for desc in cursor.description]
                        result = [result]
                        for row in cursor.fetchall():
                            result.append(row)
                        data.result = tabulate(result)
                con.rollback()

        except Exception as e:
            logger.error(e)
            data.error = str(e)

        return data


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
        try:
            if request_type == SQLCommandType.SELECT:
                result = cls._select_from_db(name, code, check_code)
            elif request_type == SQLCommandType.DELETE:
                result = cls._delete_from_db(name, code, check_code)
            else:
                result = cls._update_or_insert_into_db(name, code, check_code)
            for row in result:
                for col in row:
                    if col is True:
                        data.ok = True
                        data.result = "True"
                    else:
                        data.ok = False
                        data.result = "False"
        except Exception as e:
            logger.error(e)
            data.error = str(e)
            data.ok = False
            data.result = "False"
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
