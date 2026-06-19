from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'rating', 'clinic', 'vet', 'author', 'is_published', 'created_at')
    list_filter = ('rating', 'is_published')
    search_fields = ('text', 'pros', 'cons')
    autocomplete_fields = ('clinic', 'vet', 'author')
