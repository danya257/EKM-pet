from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'pet', 'vet', 'scheduled_at', 'status', 'kind')
    list_filter = ('status', 'kind')
    search_fields = ('owner__username', 'reason')
    autocomplete_fields = ('owner', 'pet', 'vet', 'clinic', 'service')
    date_hierarchy = 'scheduled_at'
