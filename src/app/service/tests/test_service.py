from unittest.mock import call

import pytest

from app.service.main import PostgresqlService
from app.entities import (
    DebugData,
    TestsData,
    TestData
)
from app.service.entities import ExecuteResult
from app.service.exceptions import CheckerException
from app.service import messages
from app import config


def test_execute__not_data_in__ok():

    # arrange
    code = (
        'факториал(0,1):-!.\n'
        'факториал(Н,Ф):-факториал(#Н-1#,Ю),УМНОЖЕНИЕ(Ю,Н,Ф).\n'
        '?факториал(5,Р).'
    )

    # act
    exec_result = PostgresqlService._execute(
        code=code
    )

    # assert
    assert exec_result.result == 'Р=120\n'
    assert exec_result.error is None


def test_execute__not_calculating__ok():

    # arrange
    code = (
        'папа(Александр,Гриша).\n'
        'папа(Сергей,Александр).\n'
        'папа(Николай,Наталья).\n'
        'мама(Наталья,Гриша).\n'
        'дед(Д,В):-папа(Д,П),папа(П,В).\n'
        'дед(Д,В):-папа(Д,М),мама(М,В).\n'
        '?дед(Д,Гриша).\n'
    )

    # act
    exec_result = PostgresqlService._execute(
        code=code
    )

    # assert
    assert exec_result.result == (
        'Д=Сергей\n'
        'Д=Николай\n'
    )
    assert exec_result.error is None


def test_execute__data_in_is_string__ok():

    # arrange
    data_in = 'строка1'
    code = '?ВВОДСИМВ(x).'

    # act
    exec_result = PostgresqlService._execute(
        data_in=data_in,
        code=code
    )

    # assert
    assert exec_result.result == (
        'строка1\n'
        'x=строка1\n'
    )
    assert exec_result.error is None


def test_execute__data_in_is_integer__ok():

    # arrange
    data_in = '42'
    code = '?ВВОДЦЕЛ(x).'

    # act
    exec_result = PostgresqlService._execute(
        data_in=data_in,
        code=code
    )

    # assert
    assert exec_result.result == (
        '42\n'
        'x=42\n'
    )
    assert exec_result.error is None


def test_execute__data_in_is_multiline__ok():

    # arrange
    data_in = (
        'строка1\n'
        '42'
    )
    code = (
        '?ВВОДСИМВ(x).\n'
        '?ВВОДЦЕЛ(x).'
    )
    # act
    exec_result = PostgresqlService._execute(
        data_in=data_in,
        code=code
    )

    # assert
    assert exec_result.result == (
        'строка1\n'
        'x=строка1\n'
        '42\n'
        'x=42\n'
    )
    assert exec_result.error is None


def test_execute__empty_result__return_none(mocker):

    # arrange
    code = (
        'факториал(0,1):-!.\n'
        'факториал(Н,Ф):-факториал(#Н-1#,Ю),УМНОЖЕНИЕ(Ю,Н,Ф).\n'
        '?факториал(5,Р).'
    )
    get_stdin_mock = mocker.patch(
        'app.service.main.PostgresqlService._get_stdin',
        return_value=code
    )
    communicate_mock = mocker.patch(
        'subprocess.Popen.communicate',
        return_value=('', '')
    )

    # act
    exec_result = PostgresqlService._execute(
        code=code
    )

    # assert
    assert exec_result.result is None
    assert exec_result.error is None
    get_stdin_mock.assert_called_once_with(
        data_in=None,
        code=code
    )
    communicate_mock.assert_called_once_with(
        input=code,
        timeout=config.TIMEOUT
    )


def test_check__true__ok():

    # arrange
    value = 'some value'
    right_value = 'some value'
    checker_func = (
        'def checker(right_value: str, value: str) -> bool:'
        '  return right_value == value'
    )

    # act
    check_result = PostgresqlService._check(
        checker_func=checker_func,
        right_value=right_value,
        value=value
    )

    # assert
    assert check_result is True


def test_check__false__ok():

    # arrange
    value = 'invalid value'
    right_value = 'some value'
    checker_func = (
        'def checker(right_value: str, value: str) -> bool:'
        '  return right_value == value'
    )

    # act
    check_result = PostgresqlService._check(
        checker_func=checker_func,
        right_value=right_value,
        value=value
    )

    # assert
    assert check_result is False


def test_check__invalid_checker_func__raise_exception():

    # arrange
    checker_func = (
        'def my_checker(right_value: str, value: str) -> bool:'
        '  return right_value == value'
    )

    # act
    with pytest.raises(CheckerException) as ex:
        PostgresqlService._check(
            checker_func=checker_func,
            right_value='value',
            value='value'
        )

    # assert
    assert ex.value.message == messages.MSG_2


def test_check__checker_func_no_return_instruction__raise_exception():

    # arrange
    checker_func = (
        'def checker(right_value: str, value: str) -> bool:'
        '  result = right_value == value'
    )

    # act
    with pytest.raises(CheckerException) as ex:
        PostgresqlService._check(
            checker_func=checker_func,
            right_value='value',
            value='value'
        )

    # assert
    assert ex.value.message == messages.MSG_3


def test_check__checker_func_return_not_bool__raise_exception():

    # arrange
    checker_func = (
        'def checker(right_value: str, value: str) -> bool:'
        '  return None'
    )

    # act
    with pytest.raises(CheckerException) as ex:
        PostgresqlService._check(
            checker_func=checker_func,
            right_value='value',
            value='value'
        )

    # assert
    assert ex.value.message == messages.MSG_4


def test_check__checker_func__invalid_syntax__raise_exception():

    # arrange
    checker_func = (
        'def checker(right_value: str, value: str) -> bool:'
        '  include(invalid syntax here)'
        '  return True'
    )

    # act
    with pytest.raises(CheckerException) as ex:
        PostgresqlService._check(
            checker_func=checker_func,
            right_value='value',
            value='value'
        )

    # assert
    assert ex.value.message == messages.MSG_5
    assert ex.value.details == 'invalid syntax (<string>, line 1)'


def test_debug__ok(mocker):

    # arrange
    execute_result = ExecuteResult(
        result='some execute code result',
        error='some compilation error'
    )
    execute_mock = mocker.patch(
        'app.service.main.PostgresqlService._execute',
        return_value=execute_result
    )
    data = DebugData(
        code='some code',
        data_in='some data_in'
    )

    # act
    debug_result = PostgresqlService.debug(data)

    # assert
    assert debug_result.result == execute_result.result
    assert debug_result.error == execute_result.error
    execute_mock.assert_called_once_with(
        code=data.code,
        data_in=data.data_in
    )


def test_testing__ok(mocker):

    # arrange
    execute_result = ExecuteResult(
        result='some execute code result',
        error='some compilation error'
    )
    execute_mock = mocker.patch(
        'app.service.main.PostgresqlService._execute',
        return_value=execute_result
    )
    check_result = mocker.Mock()
    check_mock = mocker.patch(
        'app.service.main.PostgresqlService._check',
        return_value=check_result
    )
    test_1 = TestData(
        data_in='some test input 1',
        data_out='some test out 1'
    )
    test_2 = TestData(
        data_in='some test input 2',
        data_out='some test out 2'
    )

    data = TestsData(
        code='some code',
        checker='some checker',
        tests=[test_1, test_2]
    )

    # act
    testing_result = PostgresqlService.testing(data)

    # assert
    tests_result = testing_result.tests
    assert len(tests_result) == 2
    assert tests_result[0].result == execute_result.result
    assert tests_result[0].error == execute_result.error
    assert tests_result[0].ok == check_result
    assert tests_result[1].result == execute_result.result
    assert tests_result[1].error == execute_result.error
    assert tests_result[1].ok == check_result
    assert execute_mock.call_args_list == [
        call(
            code=data.code,
            data_in=test_1.data_in
        ),
        call(
            code=data.code,
            data_in=test_2.data_in
        )
    ]
    assert check_mock.call_args_list == [
        call(
            checker_func=data.checker,
            right_value=test_1.data_out,
            value=execute_result.result
        ),
        call(
            checker_func=data.checker,
            right_value=test_2.data_out,
            value=execute_result.result
        )
    ]
