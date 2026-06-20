"""Адаптеры МИС. Регистр выбирает реализацию по integration.kind."""
from .base import MISAdapter, AdapterError, SlotDTO, VisitDTO, ServiceDTO
from .vetmanager import VetmanagerAdapter
from .onec import OneCMedAdapter
from .webhook import WebhookAdapter

from integrations.models import ClinicIntegration

_REGISTRY = {
    ClinicIntegration.KIND_VETMANAGER: VetmanagerAdapter,
    ClinicIntegration.KIND_ONEC:       OneCMedAdapter,
    ClinicIntegration.KIND_WEBHOOK:    WebhookAdapter,
}


def get_adapter(integration: ClinicIntegration) -> MISAdapter:
    """Возвращает адаптер для конкретной интеграции."""
    cls = _REGISTRY.get(integration.kind)
    if cls is None:
        raise AdapterError(f'Адаптер для {integration.kind!r} не зарегистрирован')
    return cls(integration)


__all__ = [
    'MISAdapter', 'AdapterError',
    'SlotDTO', 'VisitDTO', 'ServiceDTO',
    'VetmanagerAdapter', 'OneCMedAdapter', 'WebhookAdapter',
    'get_adapter',
]
