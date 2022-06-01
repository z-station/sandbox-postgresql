from typing import Optional
from marshmallow import Schema
from marshmallow.fields import (
    Nested,
    Field,
    Boolean,
    Method,
    List,
    Raw,
)
from marshmallow.decorators import (
    post_load,
    pre_dump
)
from app.entities import (
    DebugData,
    TestsData,
    TestingData,
    DeleteData,
    CreateData,
    StatusData,
    StatusAllData
)
from app.utils import clean_str


class StrField(Field):

    def _deserialize(self, value: Optional[str], *args, **kwargs):
        return clean_str(value)

    def _serialize(self, value: Optional[str], *args, **kwargs):
        return clean_str(value)


class DebugSchema(Schema):

    name = StrField(load_only=True, required=True)
    code = StrField(load_only=True, required=True)
    result = Raw(dump_only=True)
    error = StrField(dump_only=True)

    @post_load
    def make_debug_data(self, data, **kwargs) -> DebugData:
        return DebugData(**data)


class TestsSchema(Schema):
    data_in = StrField(load_only=True, required=True)
    ok = Boolean(dump_only=True)
    error = StrField(dump_only=True)

    @post_load
    def make_test_data(self, data, **kwargs) -> TestsData:
        return TestsData(**data)


class TestingSchema(Schema):

    tests = Nested(TestsSchema, many=True, required=True)
    code = StrField(load_only=True, required=True)
    name = StrField(load_only=True, required=True)
    request_type = StrField(load_only=True, required=True)

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


class DeleteSchema(Schema):
    name = StrField(load_only=True, required=True)

    @post_load
    def make_delete_data(self, data, **kwargs) -> DeleteData:
        return DeleteData(**data)


class CreateSchema(Schema):

    name = StrField(load_only=True, required=True)
    filename = StrField(load_only=True, required=True)
    status = StrField(dump_only=True)

    @post_load
    def make_create_data(self, data, **kwargs) -> CreateData:
        return CreateData(**data)


class StatusSchema(Schema):
    name = StrField(dump_only=True, required=True)
    status = StrField(dump_only=True, required=True)

    @post_load
    def make_status_data(self, data, **kwargs) -> StatusData:
        return StatusData(**data)


class StatusAllSchema(Schema):
    name = List(StrField, dump_only=True, required=True)
    status = List(StrField, dump_only=True, required=True)

    @post_load
    def make_status_all_data(self, data, **kwargs) -> StatusAllData:
        return StatusAllData(**data)


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
        return obj.description.message

    def dump_details(self, obj):
        return obj.description.details
