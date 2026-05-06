# dashboard/views.py
# Аналитика считается из реальных моделей: User, Pet, PetDocument, MedicalRecord.
# В проекте сейчас только владельцы питомцев (собаки и кошки).

import csv
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone

from users.models import User
from pets.models import Pet, PetDocument
from medical_records.models import MedicalRecord


def _build_stats(days: int = 30) -> dict:
    """Собирает все метрики дашборда одним проходом по моделям."""
    now = timezone.now()
    period_start = (now - timedelta(days=days)).date()

    users_qs = User.objects.filter(is_superuser=False)  # супер-юзеров не считаем
    pets_qs = Pet.objects.all()
    docs_qs = PetDocument.objects.all()
    records_qs = MedicalRecord.objects.all()

    users_with_doc_counts = users_qs.annotate(
        docs_count=Count('pets__documents', distinct=True),
        pets_count=Count('pets', distinct=True),
    )

    total_users = users_qs.count()
    new_users_period = users_qs.filter(date_joined__gte=period_start).count()
    active_users = users_qs.filter(
        Q(last_login__gte=period_start) | Q(date_joined__gte=period_start)
    ).count()

    total_pets = pets_qs.count()
    dogs = pets_qs.filter(species='dog').count()
    cats = pets_qs.filter(species='cat').count()

    total_docs = docs_qs.count()
    total_records = records_qs.count()

    users_with_pets = users_with_doc_counts.filter(pets_count__gt=0).count()
    users_with_3plus_docs = users_with_doc_counts.filter(docs_count__gte=3).count()
    users_with_no_docs = users_with_doc_counts.filter(docs_count=0).count()
    avg_docs_per_user_with_pets = (
        round(total_docs / users_with_pets, 2) if users_with_pets else 0
    )

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

    # Породы — топ-7 (объединённый список собак и кошек)
    breed_distribution = list(
        pets_qs.exclude(breed='').values('breed', 'species')
        .annotate(count=Count('id')).order_by('-count')[:7]
    )

    # Топ-10 пользователей по числу документов
    top_users = list(
        users_with_doc_counts.filter(docs_count__gt=0)
        .order_by('-docs_count')[:10]
        .values('id', 'username', 'first_name', 'last_name', 'email',
                'docs_count', 'pets_count', 'date_joined')
    )

    return {
        'period_days': days,
        'period_start': period_start,
        'totals': {
            'users': total_users,
            'new_users_period': new_users_period,
            'active_users': active_users,
            'pets': total_pets,
            'dogs': dogs,
            'cats': cats,
            'docs': total_docs,
            'records': total_records,
            'users_with_pets': users_with_pets,
            'users_with_3plus_docs': users_with_3plus_docs,
            'users_with_no_docs': users_with_no_docs,
            'avg_docs_per_user_with_pets': avg_docs_per_user_with_pets,
        },
        'category_distribution': category_distribution,
        'daily_registrations': daily_registrations,
        'breed_distribution': breed_distribution,
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
        'ID', 'Логин', 'Имя', 'Фамилия', 'Email',
        'Питомцев', 'Документов', 'Дата регистрации', 'Последний вход',
    ])

    qs = User.objects.filter(is_superuser=False).annotate(
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
            u.pets_count,
            u.docs_count,
            u.date_joined.strftime('%d.%m.%Y %H:%M') if u.date_joined else '',
            u.last_login.strftime('%d.%m.%Y %H:%M') if u.last_login else '',
        ])

    return response
