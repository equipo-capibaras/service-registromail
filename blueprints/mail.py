from flask import Blueprint, Response, current_app, request
from flask.views import MethodView

from .util import class_route, json_response

blp = Blueprint('Mail', __name__)


@class_route(blp, '/api/v1/mail/receive')
class MailReceive(MethodView):
    init_every_request = False

    def post(self) -> Response:
        current_app.logger.error('Mail received')
        current_app.logger.error(request.headers)
        current_app.logger.error(request.form)

        return json_response({'message': 'Email received.', 'code': 200}, 200)
