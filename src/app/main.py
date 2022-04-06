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
    TestsSchema,
    BadRequestSchema
)
from app.service.exceptions import ServiceException


def create_app():

    app = Flask(__name__)

    @app.errorhandler(400)
    def bad_request_handler(ex: Exception):
        return BadRequestSchema().dump(ex), 400

    @app.route('/status', methods=['get'])
    def index():
        schema = StatusSchema()
        try:
            data = PostgresqlService.status_all(
                schema.load(request.get_json())
            )
        except (ServiceException, ValidationError) as ex:
            abort(400, ex)
        else:
            return schema.dump(data)

    @app.route('/status/:name', methods=['get'])
    def index():
        schema = StatusSchema()
        try:
            data = PostgresqlService.status(
                schema.load(request.get_json())
            )
        except (ServiceException, ValidationError) as ex:
            abort(400, ex)
        else:
            return schema.dump(data)

    @app.route('/create', methods=['post'])
    def index():
        schema = CreateSchema()
        try:
            data = PostgresqlService.create(
                schema.load(request.get_json())
            )
        except (ServiceException, ValidationError) as ex:
            abort(400, ex)
        else:
            return schema.dump(data)

    @app.route('/delete/:name', methods=['post'])
    def index():
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

    @app.route('/debug/', methods=['post'])
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

    @app.route('/testing/', methods=['post'])
    def testing():
        schema = TestsSchema()
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
