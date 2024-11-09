import email.utils
from importlib import resources as impresources

import headerparser
from dependency_injector.wiring import Provide
from flask import Blueprint, Response, current_app, request
from flask.views import MethodView
from lingua import Language, LanguageDetectorBuilder

from containers import Container
from models import Channel, Incident, Plan
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
        self,
        sender: tuple[str | None, str],
        receiver: tuple[str | None, str],
        subject: str,
        reply_to: str | None,
        language: str,
    ) -> None:
        self.sender = sender
        self.receiver = receiver
        self.subject = subject
        self.reply_to = reply_to
        self.language = language

    def send(self, text: str, mail_repo: MailRepository = Provide[Container.mail_repo]) -> None:
        mail_repo.send(
            sender=self.sender,
            receiver=self.receiver,
            subject=self.subject,
            text=text,
            reply_to=self.reply_to,
        )

    def send_template(self, template: str, **kwargs: object) -> None:
        response_file = impresources.files(mails) / f'{template}.{self.language}.txt'
        with response_file.open('r') as f:
            response_text = f.read().format(**kwargs)

        self.send(response_text)


@class_route(blp, '/api/v1/mail/receive')
class MailReceive(MethodView):
    init_every_request = False

    response = json_response({'message': 'Email received.', 'code': 200}, 200)

    def post(  # noqa: PLR0911
        self,
        client_repo: ClientRepository = Provide[Container.client_repo],
        user_repo: UserRepository = Provide[Container.user_repo],
        incident_repo: IncidentRepository = Provide[Container.incident_repo],
        employee_repo: EmployeeRepository = Provide[Container.employee_repo],
    ) -> Response:
        message_id = get_message_id(request.form['headers'])

        client_email = email.utils.parseaddr(request.form['to'])[1]
        client = client_repo.find_by_email(client_email)
        if client is None:
            current_app.logger.warning('Client not found: %s', client_email)
            return self.response

        if client.plan not in [Plan.EMPRESARIO, Plan.EMPRESARIO_PLUS]:
            current_app.logger.warning('Client not allowed to create incidents via mail: %s', client.name)
            return self.response

        user_email = email.utils.parseaddr(request.form['from'])[1]
        user = user_repo.find_by_email(user_email)
        if user is None:
            current_app.logger.warning('User not found: %s', user_email)
            return self.response

        assignee = employee_repo.get_random_agent(client.id)
        if assignee is None:
            current_app.logger.error('No agents available to assign to the incident.')
            return self.response

        incident_name = request.form['subject'].strip()
        incident_description = '\n'.join(request.form['text'].strip().splitlines())

        detector = LanguageDetectorBuilder.from_languages(Language.SPANISH, Language.PORTUGUESE).build()
        language = detector.detect_language_of(incident_name + '\n' + incident_description)

        mail_resp = ResponseMail(
            sender=(client.name, client.email_incidents),
            receiver=(user.name, user.email),
            subject=f'Re: {request.form['subject']}',
            reply_to=message_id,
            language='pt' if language == Language.PORTUGUESE else 'es',
        )

        if len(incident_name) < 1 or len(incident_name) > 60:  # noqa: PLR2004
            mail_resp.send_template('error_name_length', client_name=client.name)
            return self.response

        if len(incident_description) < 1 or len(incident_description) > 1000:  # noqa: PLR2004
            mail_resp.send_template('error_description_length', client_name=client.name)
            return self.response

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

        mail_resp.send_template('success', client_name=client.name)
        return self.response
