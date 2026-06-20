"""
Базовый интерфейс адаптера МИС.

Контракт нарочно узкий: 4 use-кейса × 1 health-check. Расширять по мере
появления реальных доменных нужд (рецепты, лабораторные заказы, и т.д.).

DTO — простые dataclass-объекты, чтобы адаптеры не зависели от Django
моделей напрямую и могли быть протестированы изолированно.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Optional


# =========================================================================
#  DTO
# =========================================================================

@dataclass
class SlotDTO:
    starts_at: datetime
    duration_min: int = 30
    is_available: bool = True
    external_id: str = ''


@dataclass
class VisitDTO:
    visited_at: datetime
    diagnosis: str = ''
    treatment: str = ''
    services: list[dict] = field(default_factory=list)
    total: Decimal = Decimal('0')
    documents: list[dict] = field(default_factory=list)
    external_id: str = ''
    pet_ext_id: str = ''
    vet_ext_id: str = ''
    raw: dict = field(default_factory=dict)


@dataclass
class ServiceDTO:
    name: str
    price: Decimal
    description: str = ''
    external_id: str = ''


@dataclass
class PushResult:
    """Результат push_appointment — id, который МИС присвоила нашей заявке."""
    external_id: str
    status: str = 'ok'
    raw: dict = field(default_factory=dict)


# =========================================================================
#  Исключения
# =========================================================================

class AdapterError(Exception):
    """Базовая ошибка адаптера (сеть, кривой контракт, отказ МИС)."""


class AuthError(AdapterError):
    """Не получилось авторизоваться (просрочен токен, отозваны ключи)."""


class NotFound(AdapterError):
    """Запрашиваемого объекта нет в МИС."""


# =========================================================================
#  Базовый адаптер
# =========================================================================

class MISAdapter(ABC):
    """Реализуй 5 методов — получишь рабочую интеграцию."""

    name: str = 'generic'

    def __init__(self, integration):
        # integration: ClinicIntegration — не типизируем, чтобы избежать цикла
        self.integration = integration
        self.clinic = integration.clinic

    # ---- 1. Healthcheck (используется в админке и в кроне) ---------------
    @abstractmethod
    def health_check(self) -> bool:
        """Возвращает True если МИС отвечает и креды валидны."""

    # ---- 2. Push: наша заявка → МИС --------------------------------------
    @abstractmethod
    def push_appointment(self, appointment) -> PushResult:
        """Создать в МИС pre-booking / лид по нашей заявке.

        appointment: appointments.Appointment
        Должен вернуть ext_id — мы запишем в ExternalMapping и
        больше не будем дублировать.
        """

    # ---- 3. Pull: расписание свободных слотов из МИС --------------------
    @abstractmethod
    def pull_schedule(self, vet, date_from: date, date_to: date) -> Iterable[SlotDTO]:
        """Свободные слоты конкретного врача в окне дат."""

    # ---- 4. Pull: итог визита из МИС ------------------------------------
    @abstractmethod
    def pull_visit(self, appointment) -> Optional[VisitDTO]:
        """Состоявшийся визит для нашей заявки. None — если ещё нет."""

    # ---- 5. Pull: прайс из МИС ------------------------------------------
    @abstractmethod
    def sync_services(self) -> Iterable[ServiceDTO]:
        """Полный прайс клиники из МИС."""

    # ---- утилиты для подклассов -----------------------------------------
    def _log(self, *, direction: str, kind: str, payload: Any = None,
             response: Any = None, http_code: Optional[int] = None,
             error: str = '') -> None:
        from integrations.models import IntegrationEvent
        IntegrationEvent.objects.create(
            integration=self.integration,
            direction=direction,
            kind=kind,
            status=IntegrationEvent.STATUS_ERR if error else IntegrationEvent.STATUS_OK,
            http_code=http_code,
            payload=payload or {},
            response=response or {},
            error=error,
        )

    def _save_mapping(self, *, local_kind: str, local_id: int,
                      external_id: str, external_kind: str = '') -> None:
        from integrations.models import ExternalMapping
        ExternalMapping.objects.update_or_create(
            integration=self.integration,
            local_kind=local_kind, local_id=local_id,
            defaults={'external_id': str(external_id), 'external_kind': external_kind},
        )

    def _get_external_id(self, *, local_kind: str, local_id: int) -> Optional[str]:
        from integrations.models import ExternalMapping
        try:
            m = ExternalMapping.objects.get(
                integration=self.integration,
                local_kind=local_kind, local_id=local_id,
            )
            return m.external_id
        except ExternalMapping.DoesNotExist:
            return None
