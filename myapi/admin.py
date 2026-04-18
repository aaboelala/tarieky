from django.contrib import admin
from .models import Issue, Notification, DeviceToken


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'city', 'governorate', 'reporter', 'created_at']
    list_filter = ['status', 'governorate', 'city']
    search_fields = ['description', 'city', 'governorate']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']
    search_fields = ['user__email', 'message']


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'fcm_token', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['user__email', 'fcm_token']

