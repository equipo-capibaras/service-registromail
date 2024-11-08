from dependency_injector import providers
from dependency_injector.containers import DeclarativeContainer, WiringConfiguration

from repositories.rest import (
    RestClientRepository,
    RestEmployeeRepository,
    RestIncidentRepository,
    RestUserRepository,
    SendgridMailRepository,
)


class Container(DeclarativeContainer):
    wiring_config = WiringConfiguration(packages=['blueprints'])
    config = providers.Configuration()

    user_repo = providers.ThreadSafeSingleton(
        RestUserRepository,
        base_url=config.svc.user.url,
        token_provider=config.svc.user.token_provider,
    )

    incident_repo = providers.ThreadSafeSingleton(
        RestIncidentRepository,
        base_url=config.svc.incidentmodify.url,
        token_provider=config.svc.incidentmodify.token_provider,
    )

    employee_repo = providers.ThreadSafeSingleton(
        RestEmployeeRepository,
        base_url=config.svc.client.url,
        token_provider=config.svc.client.token_provider,
    )

    client_repo = providers.ThreadSafeSingleton(
        RestClientRepository,
        base_url=config.svc.client.url,
        token_provider=config.svc.client.token_provider,
    )

    mail_repo = providers.ThreadSafeSingleton(
        SendgridMailRepository,
        token_provider=config.sendgrid.token_provider,
    )
