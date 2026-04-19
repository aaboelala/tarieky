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


def send_to_tokens(tokens, title, body, data=None):
    """
    Send a push notification to a list of FCM tokens.

    Chunks tokens into batches of 500 (FCM's limit for multicast).
    Returns a list of tokens that failed with an unregistered / invalid error
    so callers can deactivate them.

    Args:
        tokens: list[str] — FCM registration tokens.
        title: str — notification title.
        body: str — notification body text.
        data: dict[str, str] — optional key-vairue data payload.

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
            data=data,
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


def notify_issue_status_change(issue):
    """
    Called when an issue status changes.

    Constructs and sends push notifications to the owner and (optionally)
    to users in the same city, including issue data.
    """
    from myapi.models import DeviceToken

    owner = issue.reporter
    data = {
        "issue_id": str(issue.pk),
        "new_status": issue.status,
    }

    # Define titles and bodies based on status
    status_content = {
        'In Progress': {
            'owner_body': "تمت الموافقة على بلاغك",
            'city_body': "تمت الموافقة على بلاغ في مدينتك",
        },
        'Resolved': {
            'owner_body': "تم حل بلاغك",
            'city_body': "تم حل بلاغ في مدينتك",
        },
        'Rejected': {
            'owner_body': "نعتذر، تم رفض بلاغك",
            'city_body': None, # No city broadcast for rejection
        },
    }

    content = status_content.get(issue.status)
    if not content:
        return

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
            title="تحديث لبلاغك",
            body=content['owner_body'],
            data=data,
        )
        _deactivate_tokens(invalid)

    # --- City broadcast (exclude owner) ---
    if content['city_body']:
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
                title="تحديث في مدينتك",
                body=content['city_body'],
                data=data,
            )
            _deactivate_tokens(invalid)

    logger.info(
        "Issue #%d updated to %s — pushed to owner (tokens: %d) and city status: %s",
        issue.pk, issue.status, len(owner_tokens), "sent" if content['city_body'] else "skipped"
    )
