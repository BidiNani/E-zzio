from typing import Any

from core.providers.google_calendar_provider import GoogleCalendarProvider
from core.providers.google_docs_provider import GoogleDocsProvider
from core.providers.google_drive_provider import GoogleDriveProvider
from core.providers.google_gmail_provider import GoogleGmailProvider
from core.providers.igoogle_provider import IGoogleProvider


class GoogleToolsGateway:
    def __init__(self):
        self.providers: dict[str, IGoogleProvider] = {
            "drive": GoogleDriveProvider(),
            "gmail": GoogleGmailProvider(),
            "calendar": GoogleCalendarProvider(),
            "docs": GoogleDocsProvider(),
        }

    def register_provider(self, service_name: str, provider: IGoogleProvider) -> None:
        self.providers[service_name.lower()] = provider

    async def execute(self, service: str, action: str = "default", **kwargs: Any) -> dict[str, Any]:
        service_key = service.lower()
        provider = self.providers.get(service_key)
        if not provider:
            raise ValueError(f"Service Google inconnu : '{service}'. Services disponibles : {list(self.providers.keys())}")

        return await provider.execute(action=action, **kwargs)


google_gateway = GoogleToolsGateway()
