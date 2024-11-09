from typing import cast
from unittest.mock import Mock

from faker import Faker
from unittest_parametrize import ParametrizedTestCase, parametrize

from app import create_app
from models import Client, Employee, Plan, Role, User
from repositories import ClientRepository, EmployeeRepository, IncidentRepository, MailRepository, UserRepository


class TestMail(ParametrizedTestCase):
    def setUp(self) -> None:
        self.faker = Faker()

        self.app = create_app()
        self.client = self.app.test_client()

    @parametrize(
        (
            'client_plan',
            'user_found',
            'agent_found',
            'has_message_id',
            'subject_length',
            'text_length',
            'expect_log',
            'expect_created',
            'expect_response',
        ),
        [
            (Plan.EMPRESARIO, True, True, True, 30, 500, False, True, True),
            (Plan.EMPRESARIO_PLUS, True, True, False, 30, 500, False, True, True),
            (None, True, True, True, 30, 500, True, False, False),
            (Plan.EMPRENDEDOR, True, True, True, 30, 500, True, False, False),
            (Plan.EMPRESARIO, False, True, True, 30, 500, True, False, False),
            (Plan.EMPRESARIO, True, False, True, 30, 500, True, False, False),
            (Plan.EMPRESARIO, True, True, True, 30, 1001, False, False, True),
            (Plan.EMPRESARIO, True, True, True, 30, 0, False, False, True),
            (Plan.EMPRESARIO, True, True, True, 61, 500, False, False, True),
            (Plan.EMPRESARIO, True, True, True, 0, 500, False, False, True),
        ],
    )
    def test_receive(  # noqa: PLR0913
        self,
        *,
        client_plan: Plan | None,
        user_found: bool,
        agent_found: bool,
        has_message_id: bool,
        subject_length: int,
        text_length: int,
        expect_log: bool,
        expect_created: bool,
        expect_response: bool,
    ) -> None:
        client = Client(
            id=cast(str, self.faker.uuid4()),
            name=self.faker.company(),
            plan=client_plan or Plan.EMPRESARIO,
            email_incidents=self.faker.email(),
        )

        user = User(
            id=cast(str, self.faker.uuid4()),
            client_id=client.id,
            name=self.faker.name(),
            email=self.faker.email(),
        )

        agent = Employee(
            id=cast(str, self.faker.uuid4()),
            client_id=client.id,
            name=self.faker.name(),
            email=self.faker.email(),
            role=Role.AGENT,
            invitation_status='accepted',
            invitation_date=self.faker.past_datetime(),
        )

        subject = self.faker.pystr(min_chars=subject_length, max_chars=subject_length)
        message_id = self.faker.email()

        client_repo_mock = Mock(ClientRepository)
        cast(Mock, client_repo_mock.find_by_email).return_value = client if client_plan is not None else None

        user_repo_mock = Mock(UserRepository)
        cast(Mock, user_repo_mock.find_by_email).return_value = user if user_found else None

        mail_repo_mock = Mock(MailRepository)

        incident_repo_mock = Mock(IncidentRepository)

        employee_repo_mock = Mock(EmployeeRepository)
        cast(Mock, employee_repo_mock.get_random_agent).return_value = agent if agent_found else None

        data = {
            'headers': f'Message-ID: {message_id}' if has_message_id else '',
            'to': client.email_incidents,
            'from': user.email,
            'subject': subject,
            'text': self.faker.pystr(min_chars=text_length, max_chars=text_length),
        }

        with (
            self.app.container.user_repo.override(user_repo_mock),
            self.app.container.client_repo.override(client_repo_mock),
            self.app.container.mail_repo.override(mail_repo_mock),
            self.app.container.incident_repo.override(incident_repo_mock),
            self.app.container.employee_repo.override(employee_repo_mock),
        ):
            if expect_log:
                with self.assertLogs():
                    resp = self.client.post('/api/v1/mail/receive', data=data)
            else:
                with self.assertNoLogs():
                    resp = self.client.post('/api/v1/mail/receive', data=data)

        if expect_created:
            cast(Mock, incident_repo_mock.create).assert_called_once()
        else:
            cast(Mock, incident_repo_mock.create).assert_not_called()

        if expect_response:
            self.assertEqual(
                cast(Mock, mail_repo_mock.send).call_args.kwargs['reply_to'], message_id if has_message_id else None
            )

        self.assertEqual(resp.status_code, 200)
