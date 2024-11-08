import email.utils

import headerparser
from dependency_injector.wiring import Provide
from flask import Blueprint, Response, current_app, request
from flask.views import MethodView

from containers import Container
from repositories import ClientRepository, MailRepository, UserRepository

from .util import class_route, json_response

blp = Blueprint('Mail', __name__)


def get_message_id(headers: str) -> str | None:
    for field in headerparser.scan(headers):
        if field[0] is not None and field[0].lower() == 'message-id':
            return field[1]

    return None


@class_route(blp, '/api/v1/mail/receive')
class MailReceive(MethodView):
    init_every_request = False

    response = json_response({'message': 'Email received.', 'code': 200}, 200)

    def post(
        self,
        client_repo: ClientRepository = Provide[Container.client_repo],
        user_repo: UserRepository = Provide[Container.user_repo],
        mail_repo: MailRepository = Provide[Container.mail_repo],
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

        message_id = get_message_id(request.form['headers'])

        mail_repo.send(
            sender=(client.name, client.email_incidents),
            receiver=(user.name, user.email),
            subject=f'Re: {request.form['subject']}',
            text='Thank you for your email.',
            reply_to=message_id,
        )

        return self.response
