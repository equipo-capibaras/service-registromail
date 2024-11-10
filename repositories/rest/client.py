from enum import Enum
from typing import Any, cast

import dacite
import requests

from models import Client
from repositories import ClientRepository

from .base import RestBaseRepository
from .util import TokenProvider


class RestClientRepository(ClientRepository, RestBaseRepository):
    def __init__(self, base_url: str, token_provider: TokenProvider | None) -> None:
        RestBaseRepository.__init__(self, base_url, token_provider)

    def find_by_email(self, email: str) -> Client | None:
        data = {'email': email}
        resp = self.authenticated_post(f'{self.base_url}/api/v1/clients/detail', json=data)

        if resp.status_code == requests.codes.ok:
            json = cast(dict[str, Any], resp.json())
            # Convert from json naming convention to Python naming convention
            json['email_incidents'] = json.pop('emailIncidents')
            return dacite.from_dict(data_class=Client, data=json, config=dacite.Config(cast=[Enum]))

        return None
