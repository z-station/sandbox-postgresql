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
    DeleteSchema,
    CreateSchema,
    StatusSchema,
    StatusAllSchema,
    BadRequestSchema
)
from app.service.exceptions import ServiceException


def create_app():

    app = Flask(__name__)

    @app.errorhandler(400)
    def bad_request_handler(ex: Exception):
        return BadRequestSchema().dump(ex), 400

    @app.route('/status', methods=['get'])
    def status():
        schema = StatusAllSchema()
        data = PostgresqlService.status_all(
            schema.load(request.get_json())
        )
        return schema.dump(data)

    @app.route('/status/<name>', methods=['get'])
    def status(name):
        schema = StatusSchema()
        data = PostgresqlService.status(
            schema.load(request.get_json()),
            name
        )
        return schema.dump(data)

    @app.route('/create', methods=['post'])
    def create():
        schema = CreateSchema()
        try:
            data = PostgresqlService.create(
                schema.load(request.get_json())
            )
        except (ServiceException, ValidationError) as ex:
            abort(400, ex)
        else:
            return schema.dump(data)

    @app.route('/delete/<name>', methods=['post'])
    def delete(name):
        schema = DeleteSchema()
        try:
            data = PostgresqlService.delete(
                schema.load(request.get_json())
            )
        except (ServiceException, ValidationError) as ex:
            abort(400, ex)
        else:
            return schema.dump(data)

    @app.route('/', methods=['get'])
    def index():
        return render_template("index.html")

    @app.route('/debug', methods=['post'])
    def debug():
        schema = DebugSchema()
        try:
            data = PostgresqlService.debug(
                schema.load(request.get_json())
            )
        except (ServiceException, ValidationError) as ex:
            abort(400, ex)
        else:
            return schema.dump(data)

    @app.route('/testing', methods=['post'])
    def testing():
        schema = TestingSchema()
        try:
            data = PostgresqlService.testing(
                schema.load(request.get_json())
            )
        except (ServiceException, ValidationError) as ex:
            abort(400, ex)
        else:
            return schema.dump(data)
    return app


app = create_app()
