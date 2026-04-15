# pets/admin.py
from django.contrib import admin
from .models import Pet

@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ('name', 'species', 'owner', 'birth_date', 'chip_number')
    list_filter = ('species', 'created_at')
    search_fields = ('name', 'chip_number', 'owner__username', 'owner__first_name')
    raw_id_fields = ('owner',)
    readonly_fields = ('qr_uuid', 'created_at')