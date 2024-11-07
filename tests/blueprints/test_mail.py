from typing import cast
from unittest import TestCase
from unittest.mock import Mock

from faker import Faker

from app import create_app
from models import Client, Plan, User
from repositories import ClientRepository, UserRepository


class TestMail(TestCase):
    def setUp(self) -> None:
        self.faker = Faker()

        self.app = create_app()
        self.client = self.app.test_client()

    def test_receive(self) -> None:
        client = Client(
            id=cast(str, self.faker.uuid4()),
            name=self.faker.company(),
            plan=self.faker.random_element([Plan.EMPRESARIO, Plan.EMPRESARIO_PLUS]),
            email_incidents=self.faker.email(),
        )

        user = User(
            id=cast(str, self.faker.uuid4()),
            client_id=client.id,
            name=self.faker.name(),
            email=self.faker.email(),
        )

        client_repo_mock = Mock(ClientRepository)
        cast(Mock, client_repo_mock.find_by_email).return_value = client

        user_repo_mock = Mock(UserRepository)
        cast(Mock, user_repo_mock.find_by_email).return_value = user

        data = {
            'to': client.email_incidents,
            'from': user.email,
        }

        with self.app.container.user_repo.override(user_repo_mock), self.app.container.client_repo.override(client_repo_mock):
            resp = self.client.post('/api/v1/mail/receive', data=data)

        self.assertEqual(resp.status_code, 200)
