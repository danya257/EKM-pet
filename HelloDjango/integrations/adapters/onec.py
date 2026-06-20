"""
Адаптер 1С:Медицина. Ветклиника.

Интеграция — через HTTP-сервисы 1С (рекомендуемый путь) или OData.
HTTP-сервис нужно опубликовать в публикации информационной базы.
Авторизация — Basic Auth (username/password) либо Bearer-токен на стороне
прокси (nginx/MOXA), у самой 1С штатной OAuth-выдачи нет.

В integration.extra ожидаем:
    "service_root": "/hs/ekm/v1"        — корневой путь HTTP-сервиса
    "ib_user":       "ekm_integration"   — пользователь ИБ
    "db_alias":      "vetkl"             — имя публикации (если несколько)
    "basic_password": "<>"               — если используется Basic Auth
                                            (либо хранить в api_token)

⚠️  Конфигурация 1С у каждой клиники своя; перед прод-использованием
проверьте, что HTTP-сервис ekm/v1 опубликован и пользователь ekm_integration
имеет права на чтение/запись соответствующих документов.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Optional

import requests
from django.utils import timezone

from .base import (
    AdapterError, AuthError, MISAdapter,
    PushResult, ServiceDTO, SlotDTO, VisitDTO,
)


class OneCMedAdapter(MISAdapter):
    name = 'onec'
    timeout = 20

    # ---- auth ----------------------------------------------------------
    def _auth(self) -> tuple[str, str] | None:
        user = self.integration.extra.get('ib_user') or self.integration.oauth_client_id
        pwd  = self.integration.extra.get('basic_password') or self.integration.api_token
        if user and pwd:
            return (user, pwd)
        return None

    def _url(self, path: str) -> str:
        root = self.integration.base_url.rstrip('/')
        svc  = self.integration.extra.get('service_root', '/hs/ekm/v1').strip('/')
        path = path.lstrip('/')
        return f"{root}/{svc}/{path}"

    def _request(self, method: str, path: str, *, json: dict | None = None,
                 params: dict | None = None, log_kind: str = '') -> dict:
        url = self._url(path)
        try:
            r = requests.request(
                method, url, json=json, params=params,
                auth=self._auth(), timeout=self.timeout,
            )
        except requests.RequestException as e:
            self._log(direction='out', kind=log_kind or path,
                      payload={'method': method, 'json': json, 'params': params},
                      error=str(e))
            raise AdapterError(f'1С network: {e}') from e

        try:
            data = r.json() if r.content else {}
        except ValueError:
            data = {'_raw': r.text}

        self._log(direction='out', kind=log_kind or path, http_code=r.status_code,
                  payload={'method': method, 'json': json, 'params': params},
                  response=data if isinstance(data, dict) else {'list': data},
                  error='' if r.ok else f'HTTP {r.status_code}')

        if r.status_code in (401, 403):
            raise AuthError(f'1С {r.status_code}: проверьте пользователя/пароль ИБ')
        if not r.ok:
            raise AdapterError(f'1С {r.status_code}: {data}')
        return data if isinstance(data, dict) else {'data': data}

    # ---- интерфейс ------------------------------------------------------
    def health_check(self) -> bool:
        try:
            self._request('GET', 'ping', log_kind='health_check')
            return True
        except AdapterError:
            return False

    def push_appointment(self, appointment) -> PushResult:
        # Контракт нашего HTTP-сервиса 1С (рекомендация — реализовать ровно так):
        #   POST /hs/ekm/v1/appointments
        #   { owner: {...}, pet: {...}, vet_ref: "...", date: "...", reason: "...", source: "ekm" }
        payload = {
            'owner': {
                'first_name': appointment.owner.first_name,
                'last_name':  appointment.owner.last_name,
                'phone':      appointment.contact_phone,
                'email':      appointment.owner.email,
            },
            'pet': {
                'name':    getattr(appointment.pet, 'name', '') if appointment.pet else '',
                'species': getattr(appointment.pet, 'species', '') if appointment.pet else '',
                'breed':   getattr(appointment.pet, 'breed', '')   if appointment.pet else '',
                'chip':    getattr(appointment.pet, 'chip_number', '') if appointment.pet else '',
            },
            'vet_ref': self._get_external_id(local_kind='clinics.vetprofile',
                                             local_id=appointment.vet.pk) or '',
            'scheduled_at': appointment.scheduled_at.isoformat(),
            'kind':         appointment.kind,
            'reason':       appointment.reason,
            'source':       'ekm-vet',
            'ext_id':       str(appointment.pk),
        }
        body = self._request('POST', 'appointments', json=payload, log_kind='appointment_push')

        ext_id = str(body.get('ref') or body.get('id') or '')
        if ext_id:
            self._save_mapping(local_kind='appointments.appointment',
                               local_id=appointment.pk, external_id=ext_id,
                               external_kind='ДокументЗаписьНаПриём')
        return PushResult(external_id=ext_id, raw=body)

    def pull_schedule(self, vet, date_from: date, date_to: date) -> Iterable[SlotDTO]:
        vet_ref = self._get_external_id(local_kind='clinics.vetprofile', local_id=vet.pk) or ''
        params = {
            'vet_ref': vet_ref,
            'from':    date_from.isoformat(),
            'to':      date_to.isoformat(),
        }
        body = self._request('GET', 'schedule', params=params, log_kind='schedule_pull')
        for slot in body.get('slots') or []:
            yield SlotDTO(
                starts_at    = _parse_dt(slot.get('start')),
                duration_min = int(slot.get('duration_min') or 30),
                is_available = bool(slot.get('available', True)),
                external_id  = str(slot.get('id') or ''),
            )

    def pull_visit(self, appointment) -> Optional[VisitDTO]:
        ext = self._get_external_id(local_kind='appointments.appointment', local_id=appointment.pk)
        if not ext:
            return None
        body = self._request('GET', f'visits/{ext}', log_kind='visit_pull')
        if not body.get('visited_at'):
            return None
        services = body.get('services') or []
        total = sum(Decimal(str(s.get('sum') or 0)) for s in services)
        return VisitDTO(
            visited_at = _parse_dt(body.get('visited_at')),
            diagnosis  = body.get('diagnosis', ''),
            treatment  = body.get('treatment', ''),
            services   = services,
            total      = total,
            documents  = body.get('documents') or [],
            external_id = str(body.get('id') or ext),
            pet_ext_id  = str(body.get('pet_ref') or ''),
            vet_ext_id  = str(body.get('vet_ref') or ''),
            raw         = body,
        )

    def sync_services(self) -> Iterable[ServiceDTO]:
        body = self._request('GET', 'services', log_kind='services_pull')
        for row in body.get('services') or []:
            yield ServiceDTO(
                name=row.get('name') or '?',
                price=Decimal(str(row.get('price') or 0)),
                description=row.get('description', ''),
                external_id=str(row.get('id') or ''),
            )


def _parse_dt(value):
    if not value:
        return timezone.now()
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except ValueError:
            return timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt
