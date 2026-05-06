# dashboard/views.py
# Аналитика считается из реальных моделей: User, Pet, PetDocument, MedicalRecord.
# Никаких параллельных таблиц с дублированием данных.

import csv
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone

from users.models import User
from pets.models import Pet, PetDocument
from clinics.models import Clinic
from medical_records.models import MedicalRecord


def _build_stats(days: int = 30) -> dict:
    """Собирает все метрики дашборда одним проходом по моделям."""
    now = timezone.now()
    period_start = (now - timedelta(days=days)).date()

    users_qs = User.objects.all()
    pets_qs = Pet.objects.all()
    docs_qs = PetDocument.objects.all()
    records_qs = MedicalRecord.objects.all()

    # Аннотируем каждого пользователя количеством документов его питомцев.
    users_with_doc_counts = users_qs.annotate(
        docs_count=Count('pets__documents', distinct=True),
        pets_count=Count('pets', distinct=True),
    )

    total_users = users_qs.count()
    owners = users_qs.filter(user_type='owner').count()
    vets = users_qs.filter(user_type='vet').count()
    clinic_admins = users_qs.filter(user_type='clinic_admin').count()

    new_users_period = users_qs.filter(date_joined__gte=period_start).count()

    # «Активные» = заходили или хоть что-то делали в окне периода.
    active_users = users_qs.filter(
        Q(last_login__gte=period_start) | Q(date_joined__gte=period_start)
    ).count()

    total_pets = pets_qs.count()
    total_docs = docs_qs.count()
    total_records = records_qs.count()
    total_clinics = Clinic.objects.count()

    users_with_3plus_docs = users_with_doc_counts.filter(docs_count__gte=3).count()
    users_with_no_docs = users_with_doc_counts.filter(docs_count=0).count()
    avg_docs_per_user = round(total_docs / total_users, 2) if total_users else 0

    # Распределение по виду питомцев
    species_distribution = list(
        pets_qs.values('species').annotate(count=Count('id')).order_by('-count')
    )
    species_map = dict(Pet.SPECIES_CHOICES)
    for row in species_distribution:
        row['label'] = species_map.get(row['species'], row['species'])

    # Распределение документов по категориям
    category_distribution = list(
        docs_qs.values('category').annotate(count=Count('id')).order_by('-count')
    )
    category_map = dict(PetDocument.CATEGORY_CHOICES)
    for row in category_distribution:
        row['label'] = category_map.get(row['category'], row['category'])

    # Регистрации по дням (за период)
    daily_regs_qs = (
        users_qs.filter(date_joined__gte=period_start)
        .annotate(day=TruncDate('date_joined'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    daily_registrations = [
        {'date': r['day'].strftime('%d.%m'), 'count': r['count']}
        for r in daily_regs_qs
        if r['day'] is not None
    ]

    # Топ-10 пользователей по числу документов (для таблицы в дашборде)
    top_users = list(
        users_with_doc_counts.filter(docs_count__gt=0)
        .order_by('-docs_count')[:10]
        .values('id', 'username', 'first_name', 'last_name', 'email', 'user_type', 'docs_count', 'pets_count', 'date_joined')
    )

    return {
        'period_days': days,
        'period_start': period_start,
        'totals': {
            'users': total_users,
            'owners': owners,
            'vets': vets,
            'clinic_admins': clinic_admins,
            'pets': total_pets,
            'docs': total_docs,
            'records': total_records,
            'clinics': total_clinics,
            'new_users_period': new_users_period,
            'active_users': active_users,
            'users_with_3plus_docs': users_with_3plus_docs,
            'users_with_no_docs': users_with_no_docs,
            'avg_docs_per_user': avg_docs_per_user,
        },
        'species_distribution': species_distribution,
        'category_distribution': category_distribution,
        'daily_registrations': daily_registrations,
        'top_users': top_users,
    }


def analytics_dashboard(request):
    try:
        days = int(request.GET.get('days', 30))
    except (TypeError, ValueError):
        days = 30
    days = max(7, min(days, 365))

    stats = _build_stats(days=days)
    return render(request, 'dashboard/index.html', {
        'stats': stats,
        'days': days,
    })


def analytics_api(request):
    try:
        days = int(request.GET.get('days', 30))
    except (TypeError, ValueError):
        days = 30
    days = max(7, min(days, 365))
    return JsonResponse(_build_stats(days=days), safe=False, json_dumps_params={'default': str})


def export_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="ekm_users.csv"'
    response.write('﻿')  # BOM для корректного открытия в Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'ID', 'Логин', 'Имя', 'Фамилия', 'Email', 'Роль',
        'Питомцев', 'Документов', 'Дата регистрации', 'Последний вход',
    ])

    qs = User.objects.annotate(
        docs_count=Count('pets__documents', distinct=True),
        pets_count=Count('pets', distinct=True),
    ).order_by('-date_joined')

    for u in qs:
        writer.writerow([
            u.id,
            u.username,
            u.first_name,
            u.last_name,
            u.email,
            u.get_user_type_display() if hasattr(u, 'get_user_type_display') else '',
            u.pets_count,
            u.docs_count,
            u.date_joined.strftime('%d.%m.%Y %H:%M') if u.date_joined else '',
            u.last_login.strftime('%d.%m.%Y %H:%M') if u.last_login else '',
        ])

    return response
