# clinics/admin.py
from django.contrib import admin
from .models import Clinic, Specialization, VetProfile


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'phone', 'rating', 'reviews_count', 'is_24h', 'accepts_online')
    list_filter = ('city', 'is_24h', 'accepts_online', 'has_lab', 'has_surgery')
    search_fields = ('name', 'city', 'address', 'phone', 'email')
    filter_horizontal = ('admins',)
    readonly_fields = ('created_at', 'rating', 'reviews_count')


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(VetProfile)
class VetProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'clinic', 'experience_years', 'price_consultation', 'rating', 'reviews_count', 'is_published')
    list_filter = ('clinic', 'is_published', 'accepts_online', 'accepts_house_call', 'specializations')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'clinic__name')
    autocomplete_fields = ('user', 'clinic')
    filter_horizontal = ('specializations',)
    readonly_fields = ('rating', 'reviews_count', 'created_at')
