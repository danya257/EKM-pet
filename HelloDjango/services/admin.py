from django.contrib import admin

from .models import Service, ServiceAssignment


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'clinic', 'price')
    list_filter = ('clinic',)
    search_fields = ('name', 'description', 'clinic__name')
    autocomplete_fields = ('clinic',)


@admin.register(ServiceAssignment)
class ServiceAssignmentAdmin(admin.ModelAdmin):
    list_display = ('service', 'vet')
    autocomplete_fields = ('service', 'vet')
    search_fields = ('service__name', 'vet__username')
