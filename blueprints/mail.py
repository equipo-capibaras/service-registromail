import email.utils
from importlib import resources as impresources

import headerparser
from dependency_injector.wiring import Provide
from flask import Blueprint, Response, current_app, request
from flask.views import MethodView

from containers import Container
from models import Channel, Incident
from repositories import ClientRepository, IncidentRepository, MailRepository, UserRepository
from repositories.employee import EmployeeRepository

from . import mails
from .util import class_route, json_response

blp = Blueprint('Mail', __name__)


def get_message_id(headers: str) -> str | None:
    for field in headerparser.scan(headers):
        if field[0] is not None and field[0].lower() == 'message-id':
            return field[1]

    return None


class ResponseMail:
    def __init__(
        self, sender: tuple[str | None, str], receiver: tuple[str | None, str], subject: str, reply_to: str | None
    ) -> None:
        self.sender = sender
        self.receiver = receiver
        self.subject = subject
        self.reply_to = reply_to

    def send(self, text: str, mail_repo: MailRepository = Provide[Container.mail_repo]) -> None:
        mail_repo.send(
            sender=self.sender,
            receiver=self.receiver,
            subject=self.subject,
            text=text,
            reply_to=self.reply_to,
        )

    def send_template(self, template: str, **kwargs: object) -> None:
        response_file = impresources.files(mails) / f'{template}.es.txt'
        with response_file.open('r') as f:
            response_text = f.read().format(**kwargs)

        self.send(response_text)


@class_route(blp, '/api/v1/mail/receive')
class MailReceive(MethodView):
    init_every_request = False

    response = json_response({'message': 'Email received.', 'code': 200}, 200)

    def post(
        self,
        client_repo: ClientRepository = Provide[Container.client_repo],
        user_repo: UserRepository = Provide[Container.user_repo],
        incident_repo: IncidentRepository = Provide[Container.incident_repo],
        employee_repo: EmployeeRepository = Provide[Container.employee_repo],
    ) -> Response:
        current_app.logger.error('Mail received')
        current_app.logger.error(request.headers)
        current_app.logger.error(request.form)

        message_id = get_message_id(request.form['headers'])

        client_email = email.utils.parseaddr(request.form['to'])[1]
        client = client_repo.find_by_email(client_email)
        if client is None:
            current_app.logger.warning('Client not found: %s', client_email)
            return self.response

        user_email = email.utils.parseaddr(request.form['from'])[1]
        user = user_repo.find_by_email(user_email)
        if user is None:
            current_app.logger.warning('User not found: %s', user_email)
            return self.response

        current_app.logger.info('Client: %s, User: %s', client.name, user.name)

        assignee = employee_repo.get_random_agent(client.id)
        if assignee is None:
            current_app.logger.error('No agents available to assign to the incident.')
            return self.response

        incident_name = request.form['subject']
        incident_description = request.form['text']

        incident = Incident(
            client_id=client.id,
            name=incident_name,
            channel=Channel.EMAIL,
            reported_by=user.id,
            created_by=user.id,
            description=incident_description,
            assigned_to=assignee.id,
        )

        incident_repo.create(incident)

        mail_resp = ResponseMail(
            sender=(client.name, client.email_incidents),
            receiver=(user.name, user.email),
            subject=f'Re: {request.form['subject']}',
            reply_to=message_id,
        )

        mail_resp.send_template('success', client_name=client.name)

        return self.response
