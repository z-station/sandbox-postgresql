from typing import Optional
from marshmallow import Schema, validate
from marshmallow.fields import (
    Nested,
    Field,
    Boolean,
    Method,
    Raw,
)
from marshmallow.decorators import (
    post_load,
    pre_dump
)
from app.entities import (
    DebugData,
    TestData,
    TestingData,
    CreateData,
    StatusData,
)
from app.utils import clean_str
from app.service.enums import (
    DebugFormat,
    SQLCommandType
)


class StrField(Field):

    def _deserialize(self, value: Optional[str], *args, **kwargs):
        return clean_str(value)

    def _serialize(self, value: Optional[str], *args, **kwargs):
        return clean_str(value)


class DebugSchema(Schema):

    name = StrField(load_only=True, required=True)
    code = StrField(load_only=True, required=True)
    format = StrField(
        load_only=True,
        required=True,
        validate=validate.OneOf(DebugFormat.VALUES)
    )
    result = Raw(dump_only=True)
    error = StrField(dump_only=True)

    @post_load
    def make_debug_data(self, data, **kwargs) -> DebugData:
        return DebugData(**data)


class TestsSchema(Schema):
    data_in = StrField(load_only=True, required=True)
    ok = Boolean(dump_only=True)
    error = StrField(dump_only=True)
    result = Raw(dump_only=True)

    @post_load
    def make_test_data(self, data, **kwargs) -> TestData:
        return TestData(**data)


class TestingSchema(Schema):

    tests = Nested(TestsSchema, many=True, required=True)
    code = StrField(load_only=True, required=True)
    name = StrField(load_only=True, required=True)
    request_type = StrField(
        load_only=True,
        required=True,
        validate=validate.OneOf(SQLCommandType.VALUES)
    )
    ok = Boolean(dump_only=True)

    @post_load
    def make_tests_data(self, data, **kwargs) -> TestingData:
        return TestingData(**data)

    @pre_dump
    def calculate_properties(self, data: TestingData, **kwargs):
        data.num = len(data.tests)

        for test in data.tests:
            if test.ok:
                data.num_ok += 1

        data.ok = data.num == data.num_ok
        return data


class CreateSchema(Schema):

    name = StrField(load_only=True, required=True)
    filename = StrField(load_only=True, required=True)

    @post_load
    def make_create_data(self, data, **kwargs) -> CreateData:
        return CreateData(**data)


class StatusSchema(Schema):
    name = StrField(dump_only=True, required=True)
    status = StrField(dump_only=True, required=True)

    @post_load
    def make_status_data(self, data, **kwargs) -> StatusData:
        return StatusData(**data)


class BadRequestSchema(Schema):

    error = Method('dump_error')
    details = Method('dump_details')

    def dump_error(self, obj):
        return 'Validation error'

    def dump_details(self, obj):
        return obj.description.messages


class ServiceExceptionSchema(Schema):

    error = Method('dump_error')
    details = Method('dump_details')

    def dump_error(self, obj):
        if hasattr(obj.description, 'message'):
            return obj.description.message
        else:
            return str(obj.description)

    def dump_details(self, obj):
        if hasattr(obj.description, 'details'):
            return obj.description.details
        else:
            return None
