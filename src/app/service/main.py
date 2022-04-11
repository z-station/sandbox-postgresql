import os
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


class PostgresqlService:

    @classmethod
    def status(cls, name) -> StatusData:
        """
        name: str, database name that's being checked
        data.name = name
        data.status: str, status of the checked database 'active'/'not_exists'
        """
        data = StatusData
        with psycopg2.connect(host=config.PSQL_HOST, user=config.PSQL_USER,
                              password=config.PSQL_PASSWORD, port=config.PSQL_PORT) as con:
            with con.cursor() as cursor:
                sqlCreateDatabase = "SELECT datname FROM pg_database where datname = '" + name + "';"
                cursor.execute(sqlCreateDatabase)
                result = len(cursor.fetchall())
                if result > 0:
                    data.name = name
                    data.status = 'active'
                else:
                    data.name = name
                    data.status = 'not exists'

        return data

    @classmethod
    def status_all(cls) -> StatusAllData:
        """
        returns a list of all databases on the server and their status 'active'/'not exists'
        """
        data = StatusAllData()
        data.status = []
        data.name = []

        with psycopg2.connect(host=config.PSQL_HOST, user=config.PSQL_USER,
                              password=config.PSQL_PASSWORD, port=config.PSQL_PORT) as con:
            with con.cursor() as cursor:
                sqlCreateDatabase = "SELECT datname FROM pg_database ;"
                cursor.execute(sqlCreateDatabase)
                result = cursor.fetchall()
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
        try:
            pth = config.APP_PATH
            backup_dir = os.path.join(pth, "backup")
            filename = data.filename
            file_dir = f'{backup_dir}'
            cmd = f'mkdir -p {file_dir}'
            os.system(cmd)
            file_path = f'{file_dir}/{filename}'
            pwd = config.PSQL_PASSWORD
            usr = config.PSQL_USER
            prt = config.PSQL_PORT
            host = config.PSQL_HOST
            name = data.name
            cmnd = f'export PGPASSWORD={pwd} && ' \
                    f'dropdb -f --if-exists -U {usr} -h {host} -p {prt} {name} && ' \
                    f'createdb -U {usr} -h {host} -p {prt} {name} && ' \
                    f'psql -U {usr} -h {host} -p {prt} {name} < {file_path} '
            os.system(cmnd)
            data.status = 'active'

        except Exception as e:
            data.status = 'not exists'
            data.message = str(e)
            data.details = "some details"

        return data

    @classmethod
    def delete(cls, data: DeleteData) -> DeleteData:
        """
        drops selected database
        data.name: str, name of a database that's being dropped
        returns status of the database 'active' - error occurred, 'not exists' - success
        """
        passed_creation = False
        try:
            """
                drop database can't be used in a transaction (with connect...)
            """
            con = psycopg2.connect(host=config.PSQL_HOST, user=config.PSQL_USER,
                                   password=config.PSQL_PASSWORD, port=config.PSQL_PORT)
            passed_creation = True
            con.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = con.cursor()
            sqlCreateDatabase = "drop database " + data.name + ";"
            cursor.execute(sqlCreateDatabase)

            sqlCheckDatabase = "SELECT datname FROM pg_database where datname = '" + data.name + "';"
            cursor.execute(sqlCheckDatabase)
            result = len(cursor.fetchall())
            if result > 0:
                data.status = 'active'
            else:
                data.status = 'not exists'
        except Exception as e:
            if passed_creation:
                con.close()
            data.status = 'active'

        return data

    @classmethod
    def _select_from_db(cls, db_name, student_command, true_command):
        """
        execute select query
        db_name - database for the query
        student_command - query sent by the user
        true_command - command that successfully solves the task
        """

        with psycopg2.connect(host=config.PSQL_HOST, user=config.PSQL_USER, database=db_name,
                              password=config.PSQL_PASSWORD, port=config.PSQL_PORT) as con:
            with con.cursor() as cursor:
                cursor.execute(f"""
                    SELECT CASE WHEN NOT EXISTS (
                            {student_command}
                            except
                            {true_command}
                        )
                        THEN TRUE
                        ELSE FALSE
                    END;
                """)
                result = cursor.fetchall()
                con.rollback()

        return result

    @classmethod
    def _change_db(cls, db_name, student_command, check_command):
        """
        execute query DELTE/UPDATE/INSERT
        db_name - database for the query
        student_command - query sent by the user
        true_command - command that checks changed database
        """
        with psycopg2.connect(host=config.PSQL_HOST, user=config.PSQL_USER, database=db_name,
                              password=config.PSQL_PASSWORD, port=config.PSQL_PORT) as con:
            with con.cursor() as cursor:
                cursor.execute(student_command)
                cursor.execute(f"""
                                SELECT CASE WHEN NOT EXISTS (
                                        {check_command}
                                    )
                                    THEN TRUE
                                    ELSE FALSE
                                END
                            """)
                result = cursor.fetchall()
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
            if data.request_type == 'select':
                result = cls._select_from_db(data.name, data.code, data.check_code)

            else:
                result = cls._change_db(data.name, data.code, data.check_code)

            data.result = []
            for row in result:
                for col in row:
                    data.result.append(col)

        except Exception as e:
            raise exceptions.ExecutionException(details=str(e))

        return data

    @classmethod
    def _test(cls, data: TestsData, name, code, check_code, request_type) -> TestsData:
        """
        runs a test during testing
        name: str, query database
        code: str, user's query
        check_code: str, code for checking the query result
        request_type: type of a query - 'select' / 'something else' , meaning DELETE/UPDATE/INSERT
        returns bool result of the query - success/failure
        """
        try:
            if request_type == 'select':
                result = cls._select_from_db(name, code, check_code)
            else:
                result = cls._change_db(name, code, check_code)

            for row in result:
                for col in row:
                    if col:
                        data.ok = True
                    else:
                        data.ok = False

        except Exception as e:
            raise exceptions.ExecutionException(details=str(e))

        return data

    @classmethod
    def testing(cls, data: TestingData) -> TestingData:
        """
        runs _test for all items in data.tests (TestsData)
        returns results of running all tests
        """
        for test in data.tests:
            test_db_name = test.data_in
            user_query = data.code
            result_checking_query = data.check_code
            request_type = test.request_type
            result = cls._test(test, test_db_name, user_query, result_checking_query, request_type)
            test.ok = result.ok
            test.error = result.error
            print(result.ok)

        return data
