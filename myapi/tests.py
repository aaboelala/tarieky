"""
Tests for the myapi app.

Covers:
  - Issue model
  - Notification model
  - DeviceToken model
  - haversine_distance utility
  - IsSupervisor permission
  - IssueListCreateView (list + create + filters)
  - IssueDetailView
  - MyIssuesListView
  - NearbyIssuesView
  - IssueStatusUpdateView (with transition validation)
  - UserProfileView (GET + PATCH)
  - NotificationListView / NotificationReadView
  - UserIssueStatsView
  - RegisterDeviceTokenView
  - IssueStatusUpdateSerializer validation
  - services.send_to_tokens / notify_issue_status_change
  - signals.issue_status_changed
"""

import io
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from PIL import Image

from authentication.models import User, Supervisor
from .models import Issue, Notification, DeviceToken
from .views import haversine_distance, IsSupervisor
from .serializers import IssueStatusUpdateSerializer


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_image(name="test.jpg"):
    """Return a minimal valid JPEG file for upload tests."""
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


def _create_user(email="user@test.com", **kw):
    defaults = dict(password="testpass1", governorate="Cairo", city="Maadi")
    defaults.update(kw)
    return User.objects.create_user(email=email, **defaults)


def _create_supervisor(email="sup@test.com", **kw):
    user = _create_user(email=email, **kw)
    Supervisor.objects.create(user=user)
    return user


def _login(client, email, password="testpass1"):
    resp = client.post(
        reverse("token_obtain_pair"),
        {"email": email, "password": password},
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return resp


def _create_issue(reporter, **kw):
    defaults = dict(
        photo=_make_image(),
        description="test issue",
        latitude=30.0,
        longitude=31.0,
        city="Maadi",
        governorate="Cairo",
        status="Pending",
        category="pothole",
    )
    defaults.update(kw)
    return Issue.objects.create(reporter=reporter, **defaults)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class IssueModelTests(TestCase):
    def setUp(self):
        self.user = _create_user()
        self.issue = _create_issue(self.user)

    def test_str_representation(self):
        s = str(self.issue)
        self.assertIn("Issue #", s)
        self.assertIn("Pending", s)
        self.assertIn("Maadi", s)

    def test_default_ordering(self):
        """Most recent first."""
        i2 = _create_issue(self.user, description="second")
        qs = Issue.objects.all()
        self.assertEqual(qs.first().pk, i2.pk)

    def test_status_choices(self):
        self.assertIn(
            self.issue.status,
            [c[0] for c in Issue.STATUS_CHOICES],
        )


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = _create_user()
        self.issue = _create_issue(self.user)
        self.notification = Notification.objects.create(
            user=self.user,
            issue=self.issue,
            message="test notification",
            notification_type="issue_update",
        )

    def test_str_representation(self):
        s = str(self.notification)
        self.assertIn(self.user.email, s)
        self.assertIn("issue_update", s)

    def test_default_is_unread(self):
        self.assertFalse(self.notification.is_read)


class DeviceTokenModelTests(TestCase):
    def setUp(self):
        self.user = _create_user()

    def test_str_active(self):
        dt = DeviceToken.objects.create(
            user=self.user, fcm_token="abc123"
        )
        self.assertIn("active", str(dt))

    def test_str_inactive(self):
        dt = DeviceToken.objects.create(
            user=self.user, fcm_token="xyz789", is_active=False
        )
        self.assertIn("inactive", str(dt))


# ---------------------------------------------------------------------------
# Utility / permission tests
# ---------------------------------------------------------------------------


class HaversineDistanceTests(TestCase):
    def test_same_point_zero(self):
        self.assertAlmostEqual(haversine_distance(30, 31, 30, 31), 0, places=0)

    def test_known_distance(self):
        # Cairo (30.0444, 31.2357) → Alexandria (31.2001, 29.9187)
        d = haversine_distance(30.0444, 31.2357, 31.2001, 29.9187)
        # ~180 km
        self.assertGreater(d, 150_000)
        self.assertLess(d, 220_000)


class IsSupervisorPermissionTests(TestCase):
    def setUp(self):
        self.perm = IsSupervisor()

    def test_anonymous_denied(self):
        request = MagicMock()
        request.user = MagicMock(is_authenticated=False)
        self.assertFalse(self.perm.has_permission(request, None))

    def test_regular_user_denied(self):
        user = _create_user(email="regular@test.com")
        request = MagicMock()
        request.user = user
        self.assertFalse(self.perm.has_permission(request, None))

    def test_supervisor_allowed(self):
        user = _create_supervisor(email="sup_perm@test.com")
        request = MagicMock()
        request.user = user
        self.assertTrue(self.perm.has_permission(request, None))


# ---------------------------------------------------------------------------
# Serializer tests
# ---------------------------------------------------------------------------


class IssueStatusUpdateSerializerTests(TestCase):
    def setUp(self):
        self.user = _create_user()

    def test_pending_to_in_progress(self):
        issue = _create_issue(self.user, status="Pending")
        s = IssueStatusUpdateSerializer(issue, data={"status": "In Progress"})
        self.assertTrue(s.is_valid(), s.errors)

    def test_pending_to_rejected(self):
        issue = _create_issue(self.user, status="Pending")
        s = IssueStatusUpdateSerializer(issue, data={"status": "Rejected"})
        self.assertTrue(s.is_valid(), s.errors)

    def test_pending_to_resolved_invalid(self):
        issue = _create_issue(self.user, status="Pending")
        s = IssueStatusUpdateSerializer(issue, data={"status": "Resolved"})
        self.assertFalse(s.is_valid())

    def test_in_progress_to_resolved(self):
        issue = _create_issue(self.user, status="In Progress")
        s = IssueStatusUpdateSerializer(issue, data={"status": "Resolved"})
        self.assertTrue(s.is_valid(), s.errors)

    def test_in_progress_to_pending_invalid(self):
        issue = _create_issue(self.user, status="In Progress")
        s = IssueStatusUpdateSerializer(issue, data={"status": "Pending"})
        self.assertFalse(s.is_valid())

    def test_resolved_cannot_change(self):
        issue = _create_issue(self.user, status="Resolved")
        s = IssueStatusUpdateSerializer(issue, data={"status": "Pending"})
        self.assertFalse(s.is_valid())

    def test_rejected_cannot_change(self):
        issue = _create_issue(self.user, status="Rejected")
        s = IssueStatusUpdateSerializer(issue, data={"status": "In Progress"})
        self.assertFalse(s.is_valid())


# ---------------------------------------------------------------------------
# View / API tests
# ---------------------------------------------------------------------------


class IssueListCreateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("issue-list-create")
        self.user = _create_user()
        # Create an "In Progress" issue (visible to citizens)
        self.issue = _create_issue(
            self.user, status="In Progress", city="Maadi"
        )

    def test_list_unauthenticated_only_in_progress(self):
        _create_issue(self.user, status="Pending")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        # Only the In Progress issue should be returned
        self.assertEqual(len(resp.data), 1)

    def test_list_filter_by_city(self):
        resp = self.client.get(self.url, {"city": "Maadi"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_list_filter_by_governorate(self):
        resp = self.client.get(self.url, {"governorate": "Cairo"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_supervisor_sees_all_statuses(self):
        sup = _create_supervisor(email="sup_list@test.com")
        _login(self.client, "sup_list@test.com")
        _create_issue(self.user, status="Pending")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        # Should see both In Progress and Pending
        self.assertGreaterEqual(len(resp.data), 2)

    def test_supervisor_filter_by_status(self):
        sup = _create_supervisor(email="sup_filter@test.com")
        _login(self.client, "sup_filter@test.com")
        _create_issue(self.user, status="Pending")
        resp = self.client.get(self.url, {"status": "Pending"})
        self.assertEqual(resp.status_code, 200)
        for item in resp.data:
            # Status is displayed as Arabic via get_status_display
            self.assertIn("قيد الانتظار", item["status"])

    def test_create_issue_authenticated(self):
        _login(self.client, "user@test.com")
        payload = {
            "photo": _make_image(),
            "description": "broken road",
            "category": "road_damage",
            "latitude": 30.05,
            "longitude": 31.23,
            "city": "Maadi",
            "governorate": "Cairo",
        }
        resp = self.client.post(self.url, payload, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_create_issue_unauthenticated_denied(self):
        payload = {
            "photo": _make_image(),
            "description": "broken road",
            "category": "road_damage",
            "latitude": 30.05,
            "longitude": 31.23,
            "city": "Maadi",
            "governorate": "Cairo",
        }
        resp = self.client.post(self.url, payload, format="multipart")
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_create_issue_notifies_city_users(self):
        other = _create_user(email="other@test.com", city="Maadi")
        _login(self.client, "user@test.com")
        payload = {
            "photo": _make_image(),
            "description": "new pothole in maadi",
            "category": "pothole",
            "latitude": 30.05,
            "longitude": 31.23,
            "city": "Maadi",
            "governorate": "Cairo",
        }
        resp = self.client.post(self.url, payload, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        
        # Query the database to get the created issue
        issue = Issue.objects.filter(city="Maadi", description="new pothole in maadi").first()
        self.assertIsNotNone(issue)
        issue_id = issue.id

        # Log in as supervisor and transition status to In Progress to trigger city alert
        _create_supervisor(email="sup_test_notif@test.com")
        _login(self.client, "sup_test_notif@test.com")
        update_url = reverse("issue-status-update", args=[issue_id])
        update_resp = self.client.patch(update_url, {"status": "In Progress"})
        self.assertEqual(update_resp.status_code, 200)

        # other user in same city should have a notification
        self.assertTrue(
            Notification.objects.filter(
                user=other, notification_type="city_alert"
            ).exists()
        )


class IssueDetailViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user()
        self.issue = _create_issue(self.user)

    def test_detail_success(self):
        url = reverse("issue-detail", args=[self.issue.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], self.issue.pk)

    def test_detail_not_found(self):
        url = reverse("issue-detail", args=[99999])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)


class MyIssuesListViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user()
        self.other = _create_user(email="other2@test.com")
        _create_issue(self.user, description="mine")
        _create_issue(self.other, description="not mine")

    def test_returns_only_own_issues(self):
        _login(self.client, "user@test.com")
        resp = self.client.get(reverse("my-issues"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_unauthenticated_denied(self):
        resp = self.client.get(reverse("my-issues"))
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class NearbyIssuesViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user()
        # Issue at exactly (30.0, 31.0) — In Progress so it's visible
        _create_issue(
            self.user,
            latitude=30.0,
            longitude=31.0,
            status="In Progress",
        )

    def test_nearby_returns_issue(self):
        resp = self.client.get(
            reverse("issues-nearby"),
            {"lat": 30.0, "lon": 31.0, "radius": 500},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_nearby_too_far_returns_empty(self):
        resp = self.client.get(
            reverse("issues-nearby"),
            {"lat": 25.0, "lon": 25.0, "radius": 100},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_nearby_missing_params(self):
        resp = self.client.get(reverse("issues-nearby"))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nearby_includes_distance(self):
        resp = self.client.get(
            reverse("issues-nearby"),
            {"lat": 30.0, "lon": 31.0, "radius": 500},
        )
        self.assertIn("distance_m", resp.data[0])


class IssueStatusUpdateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user()
        self.sup = _create_supervisor(email="sup_update@test.com")
        self.issue = _create_issue(self.user, status="Pending")

    def test_supervisor_can_update(self):
        _login(self.client, "sup_update@test.com")
        url = reverse("issue-status-update", args=[self.issue.pk])
        resp = self.client.patch(url, {"status": "In Progress"})
        self.assertEqual(resp.status_code, 200)
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, "In Progress")

    def test_regular_user_cannot_update(self):
        _login(self.client, "user@test.com")
        url = reverse("issue-status-update", args=[self.issue.pk])
        resp = self.client.patch(url, {"status": "In Progress"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_transition(self):
        _login(self.client, "sup_update@test.com")
        url = reverse("issue-status-update", args=[self.issue.pk])
        resp = self.client.patch(url, {"status": "Resolved"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_status_update_creates_notifications(self):
        _login(self.client, "sup_update@test.com")
        url = reverse("issue-status-update", args=[self.issue.pk])
        self.client.patch(url, {"status": "In Progress"})
        # Reporter should get a notification
        self.assertTrue(
            Notification.objects.filter(
                user=self.user, notification_type="issue_update"
            ).exists()
        )


class UserProfileViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user(
            first_name="Ahmed", last_name="Ali",
        )
        _login(self.client, "user@test.com")

    def test_get_profile(self):
        resp = self.client.get(reverse("user-profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["email"], "user@test.com")
        self.assertEqual(resp.data["first_name"], "Ahmed")
        self.assertFalse(resp.data["is_supervisor"])

    def test_supervisor_profile_flag(self):
        sup = _create_supervisor(email="sup_prof@test.com")
        _login(self.client, "sup_prof@test.com")
        resp = self.client.get(reverse("user-profile"))
        self.assertTrue(resp.data["is_supervisor"])

    def test_patch_profile(self):
        resp = self.client.patch(
            reverse("user-profile"),
            {"first_name": "Mohamed"},
        )
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Mohamed")

    def test_unauthenticated_denied(self):
        self.client.credentials()  # clear auth
        resp = self.client.get(reverse("user-profile"))
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class NotificationViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user()
        self.issue = _create_issue(self.user)
        self.notif = Notification.objects.create(
            user=self.user,
            issue=self.issue,
            message="test",
            notification_type="issue_update",
        )
        _login(self.client, "user@test.com")

    def test_list_notifications(self):
        resp = self.client.get(reverse("notification-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_mark_as_read(self):
        url = reverse("notification-read", args=[self.notif.pk])
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, 200)
        self.notif.refresh_from_db()
        self.assertTrue(self.notif.is_read)

    def test_cannot_read_other_users_notification(self):
        other = _create_user(email="other3@test.com")
        other_notif = Notification.objects.create(
            user=other,
            message="other",
            notification_type="city_alert",
        )
        url = reverse("notification-read", args=[other_notif.pk])
        resp = self.client.patch(url)
        self.assertEqual(resp.status_code, 404)


class UserIssueStatsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user()
        _create_issue(self.user, status="Pending", category="pothole")
        _create_issue(self.user, status="In Progress", category="lighting")
        _create_issue(self.user, status="Resolved", category="pothole")
        _login(self.client, "user@test.com")

    def test_stats_totals(self):
        resp = self.client.get(reverse("my-issues-stats"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total_issues"], 3)
        self.assertEqual(resp.data["by_status"]["pending"], 1)
        self.assertEqual(resp.data["by_status"]["in_progress"], 1)
        self.assertEqual(resp.data["by_status"]["resolved"], 1)
        self.assertEqual(resp.data["by_status"]["rejected"], 0)
        self.assertEqual(resp.data["by_category"]["pothole"], 2)
        self.assertEqual(resp.data["by_category"]["lighting"], 1)


class RegisterDeviceTokenViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _create_user()
        _login(self.client, "user@test.com")

    def test_register_new_token(self):
        resp = self.client.post(
            reverse("register-device-token"),
            {"token": "fcm_token_abc123"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            DeviceToken.objects.filter(fcm_token="fcm_token_abc123").exists()
        )

    def test_register_existing_token_updates(self):
        DeviceToken.objects.create(
            user=self.user, fcm_token="fcm_existing", is_active=False
        )
        resp = self.client.post(
            reverse("register-device-token"),
            {"token": "fcm_existing"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        dt = DeviceToken.objects.get(fcm_token="fcm_existing")
        self.assertTrue(dt.is_active)

    def test_reassign_token_to_new_user(self):
        other = _create_user(email="other4@test.com")
        DeviceToken.objects.create(
            user=other, fcm_token="shared_token"
        )
        resp = self.client.post(
            reverse("register-device-token"),
            {"token": "shared_token"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        dt = DeviceToken.objects.get(fcm_token="shared_token")
        self.assertEqual(dt.user, self.user)

    def test_unauthenticated_denied(self):
        self.client.credentials()
        resp = self.client.post(
            reverse("register-device-token"),
            {"token": "some_token"},
        )
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


# ---------------------------------------------------------------------------
# Service layer tests
# ---------------------------------------------------------------------------


class SendToTokensTests(TestCase):
    """Tests for services.send_to_tokens."""

    @patch("myapi.services.messaging")
    def test_empty_tokens_returns_empty(self, mock_messaging):
        from .services import send_to_tokens
        result = send_to_tokens([], "title", "body")
        self.assertEqual(result, [])
        mock_messaging.send_each_for_multicast.assert_not_called()

    @patch("myapi.services.messaging")
    def test_successful_send(self, mock_messaging):
        from .services import send_to_tokens

        mock_response = MagicMock()
        mock_response.failure_count = 0
        mock_response.success_count = 1
        mock_messaging.send_each_for_multicast.return_value = mock_response

        result = send_to_tokens(["token1"], "title", "body")
        self.assertEqual(result, [])

    @patch("myapi.services.messaging.send_each_for_multicast")
    def test_handles_invalid_error(self, mock_send_multi):
        from .services import send_to_tokens
        from firebase_admin import messaging as real_messaging

        # Use a real exception for isinstance to match
        exc = real_messaging.UnregisteredError("gone")
        send_resp = MagicMock()
        send_resp.exception = exc

        mock_response = MagicMock()
        mock_response.failure_count = 1
        mock_response.success_count = 0
        mock_response.responses = [send_resp]
        mock_send_multi.return_value = mock_response

        result = send_to_tokens(["bad_token"], "title", "body")
        self.assertIn("bad_token", result)


class DeactivateTokensTests(TestCase):
    def test_deactivates_invalid_tokens(self):
        from .services import _deactivate_tokens

        user = _create_user(email="deact@test.com")
        dt = DeviceToken.objects.create(
            user=user, fcm_token="invalid_tok", is_active=True
        )
        _deactivate_tokens(["invalid_tok"])
        dt.refresh_from_db()
        self.assertFalse(dt.is_active)

    def test_empty_list_noop(self):
        from .services import _deactivate_tokens
        _deactivate_tokens([])  # should not raise


class NotifyIssueStatusChangeTests(TestCase):
    @patch("myapi.services.send_to_tokens", return_value=[])
    def test_in_progress_notifies_owner_and_city(self, mock_send):
        from .services import notify_issue_status_change

        user = _create_user(email="notify_owner@test.com")
        DeviceToken.objects.create(user=user, fcm_token="owner_tok")

        city_user = _create_user(email="city_user@test.com", city="Maadi")
        DeviceToken.objects.create(user=city_user, fcm_token="city_tok")

        issue = _create_issue(user, status="In Progress", city="Maadi")
        notify_issue_status_change(issue)

        # Should be called twice: once for owner, once for city
        self.assertEqual(mock_send.call_count, 2)

    @patch("myapi.services.send_to_tokens", return_value=[])
    def test_rejected_does_not_broadcast_city(self, mock_send):
        from .services import notify_issue_status_change

        user = _create_user(email="rejected_owner@test.com")
        DeviceToken.objects.create(user=user, fcm_token="rej_tok")

        issue = _create_issue(user, status="Rejected")
        notify_issue_status_change(issue)

        # Only owner notification, no city broadcast for rejection
        self.assertEqual(mock_send.call_count, 1)

    @patch("myapi.services.send_to_tokens", return_value=[])
    def test_pending_does_nothing(self, mock_send):
        from .services import notify_issue_status_change

        user = _create_user(email="pending_owner@test.com")
        issue = _create_issue(user, status="Pending")
        notify_issue_status_change(issue)

        mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# Signal tests
# ---------------------------------------------------------------------------


class IssueSignalTests(TestCase):
    @patch("myapi.signals.notify_issue_status_change")
    def test_signal_fires_on_update(self, mock_notify):
        user = _create_user(email="sig@test.com")
        issue = _create_issue(user, status="Pending")
        # Update triggers signal
        issue.status = "In Progress"
        issue.save()
        mock_notify.assert_called_once_with(issue)

    @patch("myapi.signals.notify_issue_status_change")
    def test_signal_skips_on_create(self, mock_notify):
        user = _create_user(email="sig2@test.com")
        _create_issue(user)
        mock_notify.assert_not_called()

    @patch("myapi.signals.notify_issue_status_change", side_effect=Exception("FCM down"))
    def test_signal_swallows_exception(self, mock_notify):
        """Signal should not crash if push notification fails."""
        user = _create_user(email="sig3@test.com")
        issue = _create_issue(user, status="Pending")
        # This should NOT raise even though the service blows up
        issue.status = "In Progress"
        issue.save()
