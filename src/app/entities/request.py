from typing import TypedDict, List


class RequestDebugDict(TypedDict):

    """ Описывает формат запроса к эндпоинту /debug/ """

    translator_console_input: str
    code: str


class RequestTestData(TypedDict):

    """ Описывает формат данных теста """

    test_console_input: str
    test_console_output: str


class RequestTestingDict(TypedDict):

    """ Описывает формат запроса к эндпоинту /testing/ """

    checker_code: str
    tests_data: List[RequestTestData]
    code: str
