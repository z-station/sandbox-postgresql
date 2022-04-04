import os
import subprocess
from typing import Union, Optional, List
import psycopg2
import shlex
from datetime import datetime
from app.utils import msg
from app.entities.request import (
    RequestDebugDict,
    RequestTestData,
    RequestTestingDict
)
from app.entities.response import (
    ResponseDebugDict,
    ResponseTestData,
    ResponseTestingDict
)
from app.entities.translator import (
    RunResult,
    PythonFile
)
from app import config


class PythonService:

    @staticmethod
    def _preexec_fn():
        def change_process_user():
            os.setgid(config.SANDBOX_USER_UID)
            os.setuid(config.SANDBOX_USER_UID)
        return change_process_user()

    @staticmethod
    def _clear(text: str) -> str:

        """ Удаляет из строки лишние спец. символы,
            которые добавляет Ace-editor """

        if isinstance(text, str):
            return text.replace('\r', '').rstrip('\n')
        else:
            return text

    def create_new_db(self, db_name):
        try:

            con = psycopg2.connect(host="postgresmodule-db",
                                   user="user", password="user", port="5433")
            cursor = con.cursor()
            # could also do: CREATE DATABASE WITH OWNER
            sqlCreateDatabase = "create database " + db_name + ";"
            cursor.execute(sqlCreateDatabase)

            cmd_grant_privs = "GRANT ALL PRIVILEGES ON DATABASE " + db_name + " TO user ;"
            cursor.execute(cmd_grant_privs)
            return "db created \n"


        except Exception as e:
            return e

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

    def select_from_db(self, db_name, command):
        con = psycopg2.connect(host="postgresmodule-db", database=db_name,
                               user="user", password="user", port="5433")

        cursor = con.cursor()

        cursor.execute(command)
        return cursor.fetchall()

    def change_db(self, db_name, command):
        with psycopg2.connect(host="postgresmodule-db", database=db_name,
                              user="user", password="user", port="5433") as con:
            with con.cursor() as cursor:
                cursor.execute(command)
                #sqlSelectFromDatabase = "SELECT * FROM customers"
                #cursor.execute(sqlSelectFromDatabase)
                #print(cursor.fetchall())
                con.rollback()

        return "db changed and returned to normal \n"


    @staticmethod
    def _run_checker(checker_code: str, **checker_locals) -> Union[bool, None]:

        """ Запускает код чекера на наборе переменных checker_locals
            возвращает результат работы чекера """

        try:
            exec(checker_code, globals(), checker_locals)
        except:
            return None
        else:
            return checker_locals.get('result')

    def _run_test(
        self,
        test: RequestTestData,
        checker_code: str
    ) -> ResponseTestData:

        """ Запускает тест в интерпретаторе,
            сверяет результат работы программы и значение из теста чекером,
            определяет пройден ли тест и возвращает результат """

        result = ResponseTestData(
            test_console_input=test['test_console_input'],
            test_console_output=test['test_console_output'],
            translator_console_output=None,
            translator_error_msg=None,
            ok=False
        )

        #result['translator_error_msg'] = run_result.error_msg
        #result['translator_console_output'] = run_result.console_output

        psql_cmds_output = ""
        #psql_cmds_output += self.create_new_db("socialmedia")
        #psql_cmds_output += self.load_backup("socialmedia")
        # self.drop_db("socialmedia")
        # self.create_new_db("socialmedia")
        psql_cmds_output += self.check_if_db_exists("socialmedia")
        psql_cmds_output += self.backup_db("user")
        # self.load_backup("socialmedia")
        # self.change_db("socialmedia")
        # self.select_from_db("socialmedia")

        result['translator_console_output'] = psql_cmds_output
        test_ok = self._run_checker(
            checker_code=checker_code,
            test_console_output=self._clear(test['test_console_output']),
            translator_console_output=psql_cmds_output
        )
        if test_ok is None:
            result['translator_error_msg'] = msg.CHECKER_ERROR
        elif test_ok:
            result['ok'] = True
        return result

    def debug(self, data: RequestDebugDict) -> ResponseDebugDict:

        """ Прогоняет код в компиляторе с наборов входных данных
            и возвращает результат """

        console_input: str = self._clear(data.get('translator_console_input'))
        code: str = self._clear(data['code'])
        result = ResponseDebugDict()
        run_result = self._run_code(
            console_input=console_input,
        )
        result['translator_error_msg'] = run_result.error_msg
        result['translator_console_output'] = run_result.console_output

        return result

    def testing(self, data: RequestTestingDict) -> ResponseTestingDict:

        """ Прогоняет код на серии тестов в компиляторе
            и возвращает результат """

        code: str = self._clear(data['code'])
        tests: List[RequestTestData] = data['tests_data']
        checker_code: str = data['checker_code']

        result = ResponseTestingDict(
            num=len(tests), num_ok=0,
            ok=False, tests_data=[]
        )
        for test in tests:
            response_test_data = self._run_test(
                test=test,
                checker_code=checker_code
            )
            if response_test_data['ok']:
                result['num_ok'] += 1
            result['tests_data'].append(response_test_data)

        result['ok'] = result['num'] == result['num_ok']



        return result
