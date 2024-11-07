import email.utils

from dependency_injector.wiring import Provide
from flask import Blueprint, Response, current_app, request
from flask.views import MethodView

from containers import Container
from repositories import ClientRepository, UserRepository

from .util import class_route, json_response

blp = Blueprint('Mail', __name__)


@class_route(blp, '/api/v1/mail/receive')
class MailReceive(MethodView):
    init_every_request = False

    response = json_response({'message': 'Email received.', 'code': 200}, 200)

    def post(
        self,
        client_repo: ClientRepository = Provide[Container.client_repo],
        user_repo: UserRepository = Provide[Container.user_repo],
    ) -> Response:
        current_app.logger.error('Mail received')
        current_app.logger.error(request.headers)
        current_app.logger.error(request.form)

        client_email = email.utils.parseaddr(request.form['to'])[1]
        client = client_repo.find_by_email(client_email)
        if client is None:
            current_app.logger.info('Client not found: %s', client_email)
            return self.response

        user_email = email.utils.parseaddr(request.form['from'])[1]
        user = user_repo.find_by_email(user_email)
        if user is None:
            current_app.logger.info('User not found: %s', user_email)
            return self.response

        current_app.logger.info('Client: %s, User: %s', client.name, user.name)

        return self.response
