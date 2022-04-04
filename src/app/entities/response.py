from typing import (
    TypedDict, List, Union, Optional
)


class ResponseDebugDict(TypedDict):

    """ Описывает формат ответа эндпоинта /debug/ """

    translator_console_output: Optional[str]
    translator_error_msg: Optional[str]


class ResponseTestData(TypedDict):

    """ Описывает формат результата выполнения теста """

    test_console_input: str
    test_console_output: str
    translator_console_output: Optional[str]
    translator_error_msg: Optional[str]
    ok: Union[bool, None]


class ResponseTestingDict(TypedDict):

    """ Описывает формат ответа эндпоинта /testing/ """

    num: int
    num_ok: int
    ok: bool
    tests_data: List[ResponseTestData]
