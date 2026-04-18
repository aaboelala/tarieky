"""
Django signals for the myapi app.

Fires FCM push notifications when an issue is approved (status → In Progress).
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from myapi.models import Issue
from myapi.services import notify_issue_approved

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Issue)
def issue_status_changed(sender, instance, created, **kwargs):
    """Send FCM push when an existing issue transitions to 'In Progress'."""
    if created:
        return  # new issues start as Pending — no push needed

    if instance.status == 'In Progress':
        try:
            notify_issue_approved(instance)
        except Exception:
            logger.exception(
                "Failed to send FCM notifications for issue #%d", instance.pk,
            )
