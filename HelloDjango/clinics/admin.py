# clinics/admin.py
from django.contrib import admin
from .models import Clinic

@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone', 'email', 'created_at')
    search_fields = ('name', 'address', 'phone', 'email')
    filter_horizontal = ('admins',)  # удобный виджет для ManyToMany
    readonly_fields = ('created_at',)