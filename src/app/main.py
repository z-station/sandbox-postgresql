from flask import (
    Flask,
    request,
    render_template,
    abort
)
from marshmallow import ValidationError
from app.service.main import PostgresqlService
from app.schema import (
    DebugSchema,
    TestingSchema,
    CreateSchema,
    StatusSchema,
    BadRequestSchema,
    ServiceExceptionSchema
)
from app.service.exceptions import ServiceException


def create_app():
    app = Flask(__name__)

    @app.errorhandler(400)
    def bad_request_handler(ex: ValidationError):
        return BadRequestSchema().dump(ex), 400

    @app.errorhandler(500)
    def bad_request_handler(ex: ServiceException):
        return ServiceExceptionSchema().dump(ex), 500

    @app.route('/', methods=['get'])
    def index():
        return render_template("index.html")

    @app.route('/status/', methods=['get'])
    def status():
        try:
            data = PostgresqlService.status_all()
        except ValidationError as ex:
            abort(400, ex)
        except ServiceException as ex:
            abort(500, ex)
        else:
            return StatusSchema().dumps(data, many=True)

    @app.route('/status/<name>/', methods=['get'])
    def status_name(name):
        try:
            data = PostgresqlService.status(name)
        except ValidationError as ex:
            abort(400, ex)
        except ServiceException as ex:
            abort(500, ex)
        else:
            return StatusSchema().dump(data)

    @app.route('/create/', methods=['post'])
    def create():
        schema = CreateSchema()
        data = schema.load(request.get_json())
        try:
            PostgresqlService.create(
                name=data.name,
                filename=data.filename
            )
        except ValidationError as ex:
            abort(400, ex)
        except ServiceException as ex:
            abort(500, ex)
        else:
            return ''

    @app.route('/delete/<name>/', methods=['post'])
    def delete(name):
        try:
            PostgresqlService.delete(name)
        except ValidationError as ex:
            abort(400, ex)
        except ServiceException as ex:
            abort(500, ex)
        else:
            return ''

    @app.route('/debug/', methods=['post'])
    def debug():
        schema = DebugSchema()
        try:
            data = PostgresqlService.debug(
                schema.load(request.get_json())
            )
        except ValidationError as ex:
            abort(400, ex)
        except ServiceException as ex:
            abort(500, ex)
        else:
            return schema.dump(data)

    @app.route('/testing/', methods=['post'])
    def testing():
        schema = TestingSchema()
        try:
            data = PostgresqlService.testing(
                schema.load(request.get_json())
            )
        except ValidationError as ex:
            abort(400, ex)
        except ServiceException as ex:
            abort(500, ex)
        else:
            return schema.dump(data)

    return app


app = create_app()
