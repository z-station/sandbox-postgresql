import os
import subprocess
from typing import Optional
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
import shlex
from datetime import datetime
from app import config
from app.service import exceptions
from app.service.entities import ExecuteResult
from app.service import messages


class PostgresqlService:

    @classmethod
    def status(cls, data: StatusData, name) -> StatusData:

        con = psycopg2.connect(host=config.PSQL_HOST, user=config.PSQL_USER,
                               password=config.PSQL_PASSWORD, port=config.PSQL_PORT)
        cursor = con.cursor()
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
    def status_all(cls, data: StatusAllData) -> StatusAllData:
        con = psycopg2.connect(host=config.PSQL_HOST, user=config.PSQL_USER,
                               password=config.PSQL_PASSWORD, port=config.PSQL_PORT)
        cursor = con.cursor()
        sqlCreateDatabase = "SELECT datname FROM pg_database ;"
        cursor.execute(sqlCreateDatabase)
        result = cursor.fetchall()

        for name in result:
            a: StatusData
            cls.status(a, str(name[0]))
            data.status.insert(a)

        return data

    @classmethod
    def create(cls, data: CreateData) -> CreateData:

        con = psycopg2.connect(host=config.PSQL_HOST, user=config.PSQL_USER,
                               password=config.PSQL_PASSWORD, port=config.PSQL_PORT)
        cursor = con.cursor()
        sqlCreateDatabase = "create database " + data.name + ";"
        cursor.execute(sqlCreateDatabase)

        cmd_grant_privs = "GRANT ALL PRIVILEGES ON DATABASE " + data.name + " TO " + config.PSQL_USER + " ;"
        cursor.execute(cmd_grant_privs)

        # TODO директория с бекапами указывается в конфиге из переменных окружения
        pth = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        backup_dir = os.path.join(pth, "backup")
        filename = data.filename
        file_dir = f'{backup_dir}'
        file_path = f'{file_dir}/{filename}'

        cmd = f'mkdir -p {file_dir}'
        os.system(cmd)

        command = f'pg_dump {data.name} < {file_path}'
        proc = subprocess.Popen(shlex.split(command), shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env={
            "PGPASSWORD": config.PSQL_PASSWORD,
            "PGUSER": config.PSQL_USER,
            "PGPORT": config.PSQL_PORT,
            "PGHOST": config.PSQL_HOST
        })

        (out, err) = proc.communicate()
        if err is None:
            data.status = 'active'
        else:
            data.status = 'not exists'
            data.message = err
            data.details = "some details"

        return data


    @classmethod
    def delete(cls, data: DeleteData) -> DeleteData:

        con = psycopg2.connect(host=config.PSQL_HOST, user=config.PSQL_USER,
                               password=config.PSQL_PASSWORD, port=config.PSQL_PORT)
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

        return data


    @classmethod
    def _select_from_db(cls, db_name, student_command, true_command):

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
                    END
                """)
                result = cursor.fetchall()
                con.rollback()

        return result

    @classmethod
    def _change_db(cls, db_name, student_command, check_command):
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
        try:
            if data.request_type == 'select':
                result = cls._select_from_db(data.name, data.code, data.check_code)

            else:
                result = cls._change_db(data.name, data.code, data.check_code)

            for row in result:
                for col in row:
                    data.result += str(col) + ' '
                data.result += '\n'

        # TODO Вот тут нужно поднимать ServiceException
        # TODO Отлавливать нужно конкретные виды ошибок, а не просто Exception
        except Exception as e:
            data.error = e

        return data

    @classmethod
    def test(cls, data: TestsData, name, code, check_code, request_type) -> TestsData:
        try:
            if request_type == 'select':
                result = cls._select_from_db(name, code, check_code)
            else:
                result = cls._change_db(name, code, check_code)
                # TODO Этот цикл не выполнится если будет первое условие цикла
                for row in result:
                    for col in row:
                        if col is True:
                            data.ok = True
        # TODO Отлавливать нужно конкретные виды ошибок, а не просто Exception
        except Exception as e:
            data.error = e

        return data

    @classmethod
    def testing(cls, data: TestingData) -> TestingData:
        for test in data.tests:
            # TODO вот именно тот случай когда.
            #  Очень уместо использовать именованные аргументы
            result = cls.test(test, data.name, data.code, data.check_code, test.request_type)

            if result.ok:
                data.num_ok += 1
        if data.num_ok == len(data.tests):
            data.ok = True

        return data
