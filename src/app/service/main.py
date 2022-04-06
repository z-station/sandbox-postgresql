import os
import subprocess
from typing import Optional
from app.entities import (
    DebugData,
    TestsData
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
    def create(self, name, file_name):
        try:

            con = psycopg2.connect(host=config.PSQL_HOST, user=config.PSQL_USER,
                                   password=config.PSQL_PASSWORD, port=config.PSQL_PORT)
            cursor = con.cursor()
            sqlCreateDatabase = "create database " + name + ";"
            cursor.execute(sqlCreateDatabase)

            cmd_grant_privs = "GRANT ALL PRIVILEGES ON DATABASE " + name + " TO user ;"
            cursor.execute(cmd_grant_privs)
            return "db created \n"


        except Exception as e:
            return e

    @classmethod
    def drop_db(self, db_name):
        try:

            con = psycopg2.connect(host="postgresmodule-db",
                                   user="user", password="user", port="5433")

            cursor = con.cursor()

            sqlCreateDatabase = "drop database " + db_name + ";"
            cursor.execute(sqlCreateDatabase)
            return "db dropped \n"
            # con.commit()


        except Exception as e:
            return e

    @classmethod
    def check_if_db_exists(self, db_name):
        try:

            con = psycopg2.connect(host="postgresmodule-db",
                                   user="user", password="user", port="5433")

            cursor = con.cursor()

            # datname is case sensetive so dbname should be turned lower case
            sqlCreateDatabase = "SELECT datname FROM pg_database where datname = '" + db_name + "';"
            cursor.execute(sqlCreateDatabase)
            result = len(cursor.fetchall())
            if result > 0:
                return "db exists\n"
            else:
                return "db doesn't exist\n"

        except Exception as e:
            return e

    @classmethod
    def backup_db(self, db_name):
        try:
            pth = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            backup_dir = os.path.join(pth, "backup")
            filename = f'backup.sql'
            str_date = datetime.now().strftime('%Y-%m-%d')
            file_dir = f'{backup_dir}'
            file_path = f'{file_dir}/{filename}'

            db_user = "user"
            db_host = "postgresql-db"
            db_pass = "user"
            command = f'mkdir -p {file_dir} && ' \
                      f'export PGPASSWORD={db_pass} && ' \
                      f'pg_dump -U {db_user} -h {db_host} {db_name} > {file_path}'
            os.system(command)
            #self.stdout.write(self.style.SUCCESS(f'file: {file_path}'))




            #(out, err) = proc.communicate()

            return  "db backed up"
            #return "dump loaded \n"

        except Exception as e:
            return e

    @classmethod
    def load_backup(self, db_name):
        try:
            cmnd = """pg_dump """ + db_name + """ < dumpfile.sql"""
            # os.system(cmnd)
            # proc = subprocess.Popen(shlex.split(cmnd), stdout=subprocess.PIPE)

            proc = subprocess.Popen(shlex.split(cmnd), shell=True, env={
                "PGPASSWORD": "user",
                "PGUSER": "user",
                "PGPORT": "5433",
                "PGHOST": "postgresql-db"
            })

            (out, err) = proc.communicate()
            return str(out)
        except Exception as e:
            return e

    @classmethod
    def select_from_db(self, db_name, command):
        con = psycopg2.connect(host="postgresmodule-db", database=db_name,
                               user="user", password="user", port="5433")

        cursor = con.cursor()

        cursor.execute(command)
        return cursor.fetchall()

    @classmethod
    def change_db(db_name, command):
        with psycopg2.connect(host="postgresmodule-db", database=db_name,
                              user="user", password="user", port="5433") as con:
            with con.cursor() as cursor:
                cursor.execute(command)

                con.rollback()

        return "db changed and returned to normal \n"


    @classmethod
    def debug(cls, data: DebugData) -> DebugData:
        exec_result = cls._execute(
            code=data.code,
            data_in=data.data_in
        )
        data.result = exec_result.result
        data.error = exec_result.error
        return data

    @classmethod
    def testing(cls, data: TestsData) -> TestsData:
        for test in data.tests:
            exec_result = cls._execute(
                code=data.code,
                data_in=test.data_in
            )
            test.result = exec_result.result
            test.error = exec_result.error
            test.ok = cls._check(
                checker_func=data.checker,
                right_value=test.data_out,
                value=test.result
            )
        return data
