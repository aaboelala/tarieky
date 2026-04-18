"""
Notification service layer for FCM push notifications.

All push notification logic lives here — views and signals call into
these functions rather than using firebase_admin directly.
"""

import logging
from firebase_admin import messaging

logger = logging.getLogger(__name__)

# FCM multicast limit per batch
_BATCH_SIZE = 500


def send_to_tokens(tokens, title, body):
    """
    Send a push notification to a list of FCM tokens.

    Chunks tokens into batches of 500 (FCM's limit for multicast).
    Returns a list of tokens that failed with an unregistered / invalid error
    so callers can deactivate them.

    Args:
        tokens: list[str] — FCM registration tokens.
        title: str — notification title.
        body: str — notification body text.

    Returns:
        list[str] — tokens that should be deactivated (invalid/unregistered).
    """
    if not tokens:
        return []

    invalid_tokens = []

    for i in range(0, len(tokens), _BATCH_SIZE):
        batch = tokens[i:i + _BATCH_SIZE]
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            tokens=batch,
        )

        try:
            response = messaging.send_each_for_multicast(message)
        except Exception:
            logger.exception("FCM multicast send failed for batch %d", i)
            continue

        if response.failure_count:
            for idx, send_response in enumerate(response.responses):
                if send_response.exception is not None:
                    exc = send_response.exception
                    # Mark unregistered / invalid tokens for cleanup
                    if isinstance(exc, (
                        messaging.UnregisteredError,
                        messaging.InvalidArgumentError,
                    )):
                        invalid_tokens.append(batch[idx])
                    else:
                        logger.warning(
                            "FCM send error for token %s: %s",
                            batch[idx][:20], exc,
                        )

        logger.info(
            "FCM batch %d: %d success, %d failure",
            i, response.success_count, response.failure_count,
        )

    return invalid_tokens


def _deactivate_tokens(invalid_tokens):
    """Mark invalid tokens as inactive in the database."""
    if not invalid_tokens:
        return
    from myapi.models import DeviceToken
    updated = DeviceToken.objects.filter(
        fcm_token__in=invalid_tokens, is_active=True,
    ).update(is_active=False)
    if updated:
        logger.info("Deactivated %d invalid FCM tokens", updated)


def notify_issue_approved(issue):
    """
    Called when an issue transitions to 'In Progress' (approved).

    Sends two separate push notifications:
      1. City broadcast — all active users in the same city, EXCLUDING the owner.
      2. Owner notification — only to the issue reporter.
    """
    from myapi.models import DeviceToken

    owner = issue.reporter

    # --- City broadcast (exclude owner) ---
    city_tokens = list(
        DeviceToken.objects.filter(
            user__city__iexact=issue.city,
            is_active=True,
        )
        .exclude(user=owner)
        .values_list('fcm_token', flat=True)
        .distinct()
    )

    if city_tokens:
        invalid = send_to_tokens(
            city_tokens,
            title="City Update",
            body="An issue in your city has been approved",
        )
        _deactivate_tokens(invalid)

    # --- Owner notification ---
    owner_tokens = list(
        DeviceToken.objects.filter(
            user=owner,
            is_active=True,
        ).values_list('fcm_token', flat=True)
    )

    if owner_tokens:
        invalid = send_to_tokens(
            owner_tokens,
            title="Your Issue Updated",
            body="Your issue has been approved",
        )
        _deactivate_tokens(invalid)

    logger.info(
        "Issue #%d approved — pushed to %d city tokens + %d owner tokens",
        issue.pk, len(city_tokens), len(owner_tokens),
    )
