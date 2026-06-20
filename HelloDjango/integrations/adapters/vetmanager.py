"""
Адаптер Vetmanager (https://vetmanager.com).

API: документация на https://help.vetmanager.com/ru/category/api .
Аутентификация — OAuth 2.0 с access_token; токен передаётся в заголовке
`X-REST-API-KEY` или Authorization: Bearer (зависит от endpoint).

Endpoints (упрощённо, под основные сущности):
    GET  /rest/api/client                 — клиенты
    GET  /rest/api/pet                    — питомцы
    GET  /rest/api/admission              — записи на приём
    POST /rest/api/admission              — создать запись
    GET  /rest/api/admission_schedule     — расписание (свободные слоты)
    GET  /rest/api/good                   — услуги
    GET  /rest/api/medical_card           — карта приёма

Контракт REST: { "success": true, "data": { ... } } / { "errors": [ ... ] }.

⚠️  Боевые ключи я не проверял — у меня нет тестового аккаунта Vetmanager.
Структура запросов сделана по публичной документации и шаблонам других
интеграций; перед прод-деплоем нужен один проход с реальной clinic
(включите интеграцию в админке, нажмите «Health check» и сверьте лог).
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Iterable, Optional

import requests
from django.utils import timezone

from .base import (
    AdapterError, AuthError, MISAdapter, NotFound,
    PushResult, ServiceDTO, SlotDTO, VisitDTO,
)


class VetmanagerAdapter(MISAdapter):
    name = 'vetmanager'
    timeout = 12  # секунд

    # ---- HTTP ----------------------------------------------------------
    def _headers(self) -> dict:
        token = self._access_token()
        return {
            'X-REST-API-KEY': token,
            'Authorization':  f'Bearer {token}',
            'Accept':         'application/json',
            'Content-Type':   'application/json',
        }

    def _access_token(self) -> str:
        """Если в integration лежит client_id — делаем OAuth flow,
        иначе берём api_token напрямую (legacy static-key режим)."""
        if not self.integration.oauth_client_id:
            if not self.integration.api_token:
                raise AuthError('Vetmanager: ни OAuth client_id, ни статический api_token не заданы')
            return self.integration.api_token

        # OAuth client_credentials
        cache = self.integration.extra.get('_token_cache') or {}
        if cache.get('access_token') and cache.get('expires_at', 0) > time.time() + 30:
            return cache['access_token']

        r = requests.post(
            f"{self.integration.base_url.rstrip('/')}/oauth2/token",
            data={
                'grant_type':    'client_credentials',
                'client_id':     self.integration.oauth_client_id,
                'client_secret': self.integration.api_token,
                'scope':         self.integration.extra.get('oauth_scope', 'read write'),
            },
            timeout=self.timeout,
        )
        if r.status_code != 200:
            raise AuthError(f'Vetmanager OAuth: {r.status_code} {r.text[:200]}')
        body = r.json()
        access = body['access_token']
        # сохраним в extra (без секрета)
        self.integration.extra['_token_cache'] = {
            'access_token': access,
            'expires_at':   int(time.time()) + int(body.get('expires_in', 3600)),
        }
        self.integration.save(update_fields=['extra'])
        return access

    def _request(self, method: str, path: str, *, json: dict | None = None,
                 params: dict | None = None, log_kind: str = '') -> dict:
        url = f"{self.integration.base_url.rstrip('/')}{path}"
        try:
            r = requests.request(
                method, url, headers=self._headers(),
                json=json, params=params, timeout=self.timeout,
            )
        except requests.RequestException as e:
            self._log(direction='out', kind=log_kind or path,
                      payload={'method': method, 'params': params, 'json': json},
                      error=str(e))
            raise AdapterError(f'Vetmanager network: {e}') from e

        try:
            data = r.json() if r.content else {}
        except ValueError:
            data = {'_raw': r.text}

        self._log(direction='out', kind=log_kind or path, http_code=r.status_code,
                  payload={'method': method, 'params': params, 'json': json},
                  response=data if isinstance(data, dict) else {'list': data},
                  error='' if r.ok else f'HTTP {r.status_code}')

        if r.status_code == 401:
            raise AuthError(f'Vetmanager 401: {data}')
        if r.status_code == 404:
            raise NotFound(f'Vetmanager 404: {path}')
        if not r.ok:
            raise AdapterError(f'Vetmanager {r.status_code}: {data}')

        # Vetmanager оборачивает в {success, data}; если не обёрнуто — отдадим как есть.
        if isinstance(data, dict) and 'data' in data and isinstance(data['data'], (dict, list)):
            return data
        return data

    # ---- интерфейс MISAdapter -------------------------------------------
    def health_check(self) -> bool:
        try:
            self._request('GET', '/rest/api/clinic',
                          params={'limit': 1}, log_kind='health_check')
            return True
        except AdapterError:
            return False

    def push_appointment(self, appointment) -> PushResult:
        # Vetmanager: POST /rest/api/admission
        payload = {
            'admission': {
                'admission_date': appointment.scheduled_at.date().isoformat(),
                'admission_time': appointment.scheduled_at.strftime('%H:%M'),
                'user_id':        self._vet_ext_id(appointment.vet),
                'client_first_name': appointment.owner.first_name or appointment.owner.username,
                'client_last_name':  appointment.owner.last_name or '',
                'client_phone':      appointment.contact_phone or '',
                'description':       appointment.reason,
                'source':            'ekm-vet',
                'status':            'wait',
            }
        }
        if appointment.pet:
            payload['admission']['patient_alias'] = appointment.pet.name

        body = self._request('POST', '/rest/api/admission', json=payload,
                             log_kind='appointment_push')
        ext_id = str(body.get('data', {}).get('id') or body.get('id') or '')
        if ext_id:
            self._save_mapping(local_kind='appointments.appointment',
                               local_id=appointment.pk, external_id=ext_id,
                               external_kind='admission')
        return PushResult(external_id=ext_id, raw=body)

    def pull_schedule(self, vet, date_from: date, date_to: date) -> Iterable[SlotDTO]:
        vet_ext = self._vet_ext_id(vet, required=False)
        params = {
            'from': date_from.isoformat(),
            'to':   date_to.isoformat(),
        }
        if vet_ext:
            params['user_id'] = vet_ext

        body = self._request('GET', '/rest/api/admission_schedule', params=params,
                             log_kind='schedule_pull')
        rows = body.get('data', body) if isinstance(body, dict) else body

        for row in rows or []:
            yield SlotDTO(
                starts_at=_parse_dt(row.get('start') or row.get('admission_date_full')),
                duration_min=int(row.get('duration') or 30),
                is_available=row.get('status') in (None, '', 'free', 'available'),
                external_id=str(row.get('id') or ''),
            )

    def pull_visit(self, appointment) -> Optional[VisitDTO]:
        ext = self._get_external_id(local_kind='appointments.appointment',
                                    local_id=appointment.pk)
        if not ext:
            return None
        try:
            body = self._request('GET', f'/rest/api/admission/{ext}',
                                 log_kind='visit_pull')
        except NotFound:
            return None

        adm = body.get('data', body) if isinstance(body, dict) else {}
        if adm.get('status') not in ('finished', 'done', 'completed'):
            return None  # ещё не завершён

        services = []
        total = Decimal('0')
        for g in adm.get('goods') or []:
            price = Decimal(str(g.get('price') or 0))
            qty   = Decimal(str(g.get('quantity') or 1))
            sub   = price * qty
            total += sub
            services.append({'name': g.get('title') or g.get('name') or '?',
                             'price': float(price), 'qty': float(qty), 'sum': float(sub)})

        documents = [{'url': d.get('url'), 'title': d.get('title') or 'Документ'}
                     for d in adm.get('documents') or [] if d.get('url')]

        return VisitDTO(
            visited_at = _parse_dt(adm.get('admission_date_full') or adm.get('updated_at')),
            diagnosis  = adm.get('diagnos') or adm.get('diagnosis') or '',
            treatment  = adm.get('recommendations') or adm.get('treatment') or '',
            services   = services,
            total      = total,
            documents  = documents,
            external_id = str(adm.get('id') or ext),
            pet_ext_id  = str(adm.get('patient_id') or ''),
            vet_ext_id  = str(adm.get('user_id') or ''),
            raw         = adm,
        )

    def sync_services(self) -> Iterable[ServiceDTO]:
        body = self._request('GET', '/rest/api/good',
                             params={'limit': 1000}, log_kind='services_pull')
        rows = body.get('data', body) if isinstance(body, dict) else body
        for row in rows or []:
            yield ServiceDTO(
                name=row.get('title') or row.get('name') or '?',
                price=Decimal(str(row.get('price') or 0)),
                description=row.get('description') or '',
                external_id=str(row.get('id') or ''),
            )

    # ---- helpers --------------------------------------------------------
    def _vet_ext_id(self, vet, required: bool = True) -> str:
        ext = self._get_external_id(local_kind='clinics.vetprofile', local_id=vet.pk)
        if ext:
            return ext
        if required:
            raise AdapterError(
                f'Не задан ExternalMapping для врача #{vet.pk}. '
                'Зайдите в админку → ExternalMapping и пропишите user_id Vetmanager.'
            )
        return ''


def _parse_dt(value):
    """Парсит '2026-06-20 14:30' / ISO / None — возвращает aware datetime."""
    if not value:
        return timezone.now()
    if isinstance(value, datetime):
        dt = value
    else:
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
                    '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%S%z'):
            try:
                dt = datetime.strptime(str(value), fmt)
                break
            except ValueError:
                continue
        else:
            return timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt
