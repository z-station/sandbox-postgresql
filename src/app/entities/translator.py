import os
import uuid
import re
from typing import Optional
from dataclasses import dataclass

from app.utils import msg
from app.config import SANDBOX_DIR


class PythonFile:

    """ Описывает файлы, необходимые для запуска программы """

    def __init__(self, code: str):
        self.filepath = os.path.join(SANDBOX_DIR, f'{uuid.uuid4()}.py')
        with open(self.filepath, 'w') as file:
            file.write(code)

    def remove(self):
        os.remove(self.filepath)


@dataclass
class RunResult:

    """ Описывает результат интерпретации кода программы """

    _error_msg: Optional[str] = None
    _console_output: Optional[str] = None

    @staticmethod
    def _remove_spec_chars(value: str) -> str:

        """ Удалить лишние спец-символы """

        return value.replace('\r', '').rstrip('\n')

    def _resolve_error_msg(self, value: str) -> str:

        """ Обработка текста сообщения об ошибке """

        error_msg = self._remove_spec_chars(
            value=re.sub(pattern=r'\s*File.+.py",', repl="", string=value)
        )
        if 'Terminated' in error_msg:
            error_msg = msg.TIMEOUT
        elif 'Read-only file system' in error_msg:
            error_msg = msg.READ_ONLY_FS
        return error_msg

    @property
    def error_msg(self):
        return self._error_msg

    @error_msg.setter
    def error_msg(self, value: Optional[str]):
        if value is not None:
            self._error_msg = self._resolve_error_msg(value)

    @property
    def console_output(self):
        return self._console_output

    @console_output.setter
    def console_output(self, value: Optional[str]):
        if value is not None:
            self._console_output = self._remove_spec_chars(value)
