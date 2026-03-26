from django.contrib import admin
from .models import Issue


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'city', 'governorate', 'reporter', 'created_at']
    list_filter = ['status', 'governorate', 'city']
    search_fields = ['description', 'city', 'governorate']
