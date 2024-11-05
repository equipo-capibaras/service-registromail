from unittest import TestCase

from app import create_app


class TestMail(TestCase):
    def setUp(self) -> None:
        app = create_app()
        self.client = app.test_client()

    def test_receive(self) -> None:
        resp = self.client.post('/api/v1/mail/receive')

        self.assertEqual(resp.status_code, 200)
