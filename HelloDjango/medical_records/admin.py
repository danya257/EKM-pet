# medical_records/admin.py
from django.contrib import admin
from .models import MedicalRecord

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('pet', 'record_type', 'title', 'date', 'created_by')
    list_filter = ('record_type', 'date', 'created_at')
    search_fields = ('title', 'description', 'pet__name', 'created_by__username')
    raw_id_fields = ('pet', 'created_by')
    date_hierarchy = 'date'