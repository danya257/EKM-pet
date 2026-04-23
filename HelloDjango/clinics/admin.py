# clinics/admin.py
from django.contrib import admin
from .models import Clinic

@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'address', 'phone', 'email', 'created_at')
    list_filter = ('city',)
    search_fields = ('name', 'city', 'address', 'phone', 'email')
    filter_horizontal = ('admins',)
    readonly_fields = ('created_at',)