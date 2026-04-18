from django.db import models
from django.conf import settings


class Issue(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
        ('Rejected', 'Rejected'),
    ]

    CATEGORY_CHOICES = [
        ('lighting', 'إنارة'),
        ('pothole', 'نقرة'),
        ('speed_bump', 'مطب'),
        ('traffic_sign', 'لافتة مرورية'),
        ('road_damage', 'تلف طريق'),
        ('other', 'أخرى'),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reported_issues',
    )
    photo = models.ImageField(upload_to='issue_photos/')
    description = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending',
    )

    latitude = models.FloatField()
    longitude = models.FloatField()
    city = models.CharField(max_length=100)
    governorate = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other',
    )
    

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Issue #{self.pk} - {self.status} ({self.city})"


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('issue_update', 'Issue Update'),
        ('city_alert', 'City Alert'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    issue = models.ForeignKey(
        Issue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"To {self.user.email} - {self.notification_type} - Read: {self.is_read}"


class DeviceToken(models.Model):
    """Stores FCM device tokens for push notifications."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_tokens',
    )
    fcm_token = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f"Token for {self.user.email} ({'active' if self.is_active else 'inactive'})"
