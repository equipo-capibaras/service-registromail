from models import Client


class ClientRepository:
    def find_by_email(self, email: str) -> Client | None:
        raise NotImplementedError  # pragma: no cover
