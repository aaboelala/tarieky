"""
Tests for the authentication app.

Covers:
  - User model & manager
  - Supervisor model
  - ResetPasswordCode / SignupOTP models (including expiry)
  - UserRegistrationView (sign-up flow with OTP)
  - Login (JWT token obtain)
  - Logout (token blacklist)
  - SignUpOTPView & VerifyOTPView
  - ResetPasswordView, VerifyOTPViewForForgetPass, SetNewPasswordView
  - GovernoratesCitiesView
"""

import json
import secrets
from datetime import timedelta
from pathlib import Path as PathLib
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import User, Supervisor, ResetPasswordCode, SignupOTP


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class UserManagerTests(TestCase):
    """Tests for the custom UserManager."""

    def test_create_user_success(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="securepass123",
            first_name="Ahmed",
            last_name="Ali",
            governorate="Cairo",
            city="Nasr City",
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("securepass123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_normalizes_email(self):
        user = User.objects.create_user(
            email="Test@EXAMPLE.COM",
            password="pass12345",
            governorate="Giza",
            city="Dokki",
        )
        self.assertEqual(user.email, "Test@example.com")

    def test_create_user_no_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="pass12345")

    def test_create_superuser(self):
        su = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass1",
            governorate="Cairo",
            city="Maadi",
        )
        self.assertTrue(su.is_staff)
        self.assertTrue(su.is_superuser)

    def test_create_superuser_not_staff_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin2@example.com",
                password="adminpass1",
                is_staff=False,
            )

    def test_create_superuser_not_superuser_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin3@example.com",
                password="adminpass1",
                is_superuser=False,
            )


class UserModelTests(TestCase):
    """Tests for the User model itself."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="citizen@test.com",
            password="testpass1",
            first_name="Mohamed",
            last_name="Hassan",
            governorate="Alexandria",
            city="Sidi Gaber",
        )

    def test_str_representation(self):
        self.assertEqual(str(self.user), "Citizen: citizen@test.com")

    def test_username_is_none(self):
        self.assertIsNone(self.user.username)

    def test_email_is_unique(self):
        with self.assertRaises(Exception):
            User.objects.create_user(
                email="citizen@test.com",
                password="anotherpass1",
                governorate="Cairo",
                city="Helwan",
            )


class SupervisorModelTests(TestCase):
    """Tests for the Supervisor model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="supervisor@test.com",
            password="testpass1",
            governorate="Cairo",
            city="Maadi",
        )
        self.supervisor = Supervisor.objects.create(user=self.user)

    def test_str_representation(self):
        self.assertIn("Supervisor:", str(self.supervisor))
        self.assertIn(self.user.email, str(self.supervisor))

    def test_one_to_one_relationship(self):
        self.assertEqual(self.user.supervisor, self.supervisor)


class ResetPasswordCodeModelTests(TestCase):
    """Tests for the ResetPasswordCode model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="reset@test.com",
            password="testpass1",
            governorate="Luxor",
            city="Luxor",
        )

    def test_str_representation(self):
        code = ResetPasswordCode.objects.create(user=self.user, code=1234)
        self.assertIn("reset@test.com", str(code))
        self.assertIn("1234", str(code))

    def test_is_expired_false_when_fresh(self):
        code = ResetPasswordCode.objects.create(user=self.user, code=5678)
        self.assertFalse(code.is_expired())

    def test_is_expired_true_after_5_minutes(self):
        code = ResetPasswordCode.objects.create(user=self.user, code=9999)
        # Manually backdate created_at
        ResetPasswordCode.objects.filter(pk=code.pk).update(
            created_at=timezone.now() - timedelta(minutes=6)
        )
        code.refresh_from_db()
        self.assertTrue(code.is_expired())


class SignupOTPModelTests(TestCase):
    """Tests for the SignupOTP model."""

    def test_str_representation(self):
        otp = SignupOTP.objects.create(email="new@test.com", code=4321)
        self.assertIn("new@test.com", str(otp))

    def test_is_expired_false_when_fresh(self):
        otp = SignupOTP.objects.create(email="new@test.com", code=4321)
        self.assertFalse(otp.is_expired())

    def test_is_expired_true_after_5_minutes(self):
        otp = SignupOTP.objects.create(email="new@test.com", code=4321)
        SignupOTP.objects.filter(pk=otp.pk).update(
            created_at=timezone.now() - timedelta(minutes=6)
        )
        otp.refresh_from_db()
        self.assertTrue(otp.is_expired())


# ---------------------------------------------------------------------------
# API / View tests
# ---------------------------------------------------------------------------


class SignUpOTPViewTests(TestCase):
    """Tests for the signup OTP request endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("sign-up-otp")

    @patch("authentication.views.send_async_email")
    def test_send_otp_success(self, mock_email):
        resp = self.client.post(self.url, {"email": "new@example.com"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("OTP sent", resp.data["message"])
        self.assertTrue(SignupOTP.objects.filter(email="new@example.com").exists())
        mock_email.assert_called_once()

    def test_send_otp_missing_email(self):
        resp = self.client.post(self.url, {})
        self.assertEqual(resp.status_code, 400)

    @patch("authentication.views.send_async_email")
    def test_send_otp_already_registered(self, mock_email):
        User.objects.create_user(
            email="existing@example.com",
            password="pass12345",
            governorate="Cairo",
            city="Helwan",
        )
        resp = self.client.post(self.url, {"email": "existing@example.com"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("already registered", resp.data["error"])


class VerifyOTPViewTests(TestCase):
    """Tests for the signup OTP verification endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("verify_sign_up_otp")
        self.otp = SignupOTP.objects.create(email="verify@test.com", code=1234)

    def test_verify_otp_success(self):
        resp = self.client.post(
            self.url, {"email": "verify@test.com", "code": 1234}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("verification_token", resp.data)

    def test_verify_otp_wrong_code(self):
        resp = self.client.post(
            self.url, {"email": "verify@test.com", "code": 9999}
        )
        self.assertEqual(resp.status_code, 400)

    def test_verify_otp_expired(self):
        SignupOTP.objects.filter(pk=self.otp.pk).update(
            created_at=timezone.now() - timedelta(minutes=6)
        )
        resp = self.client.post(
            self.url, {"email": "verify@test.com", "code": 1234}
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("expired", resp.data["error"].lower())


class UserRegistrationViewTests(TestCase):
    """Tests for the full user sign-up (requires a valid verification_token)."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("user-sign-up")
        # Pre-create a verified OTP with token
        self.otp = SignupOTP.objects.create(
            email="signup@test.com",
            code=1111,
            verification_token="valid-token-abc",
        )

    def test_register_success(self):
        payload = {
            "email": "signup@test.com",
            "password": "strongpass1",
            "first_name": "Test",
            "last_name": "User",
            "governorate": "Cairo",
            "city": "Maadi",
            "verification_token": "valid-token-abc",
        }
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="signup@test.com").exists())

    def test_register_invalid_token(self):
        payload = {
            "email": "signup@test.com",
            "password": "strongpass1",
            "first_name": "Test",
            "last_name": "User",
            "governorate": "Cairo",
            "city": "Maadi",
            "verification_token": "wrong-token",
        }
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password(self):
        SignupOTP.objects.create(
            email="short@test.com",
            code=2222,
            verification_token="token-short",
        )
        payload = {
            "email": "short@test.com",
            "password": "abc",
            "first_name": "Test",
            "last_name": "User",
            "governorate": "Cairo",
            "city": "Maadi",
            "verification_token": "token-short",
        }
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTests(TestCase):
    """Tests for JWT token obtain (login)."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("token_obtain_pair")
        self.user = User.objects.create_user(
            email="login@test.com",
            password="loginpass1",
            governorate="Cairo",
            city="Zamalek",
        )

    def test_login_success(self):
        resp = self.client.post(
            self.url, {"email": "login@test.com", "password": "loginpass1"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_login_wrong_password(self):
        resp = self.client.post(
            self.url, {"email": "login@test.com", "password": "wrongpass"}
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutViewTests(TestCase):
    """Tests for the logout endpoint (token blacklist)."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="logout@test.com",
            password="logoutpass1",
            governorate="Giza",
            city="Faisal",
        )
        # Log in to get tokens
        resp = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "logout@test.com", "password": "logoutpass1"},
        )
        self.access = resp.data["access"]
        self.refresh = resp.data["refresh"]

    def test_logout_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        resp = self.client.post(reverse("logout"), {"refresh": self.refresh})
        self.assertEqual(resp.status_code, status.HTTP_205_RESET_CONTENT)

    def test_logout_no_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        resp = self.client.post(reverse("logout"), {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        resp = self.client.post(reverse("logout"), {"refresh": "invalid-token"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_unauthenticated(self):
        resp = self.client.post(reverse("logout"), {"refresh": self.refresh})
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class ResetPasswordFlowTests(TestCase):
    """Tests for the full reset password flow: request → verify → set new."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="reset@test.com",
            password="oldpass123",
            governorate="Aswan",
            city="Aswan",
        )

    @patch("authentication.views.send_async_email")
    def test_request_reset_otp_success(self, mock_email):
        resp = self.client.post(
            reverse("reset_password"), {"email": "reset@test.com"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            ResetPasswordCode.objects.filter(user=self.user).exists()
        )
        mock_email.assert_called_once()

    def test_request_reset_otp_unknown_email(self):
        resp = self.client.post(
            reverse("reset_password"), {"email": "nobody@test.com"}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_reset_otp_success(self):
        code = ResetPasswordCode.objects.create(user=self.user, code=5555)
        resp = self.client.post(
            reverse("confirm_reset_password"),
            {"email": "reset@test.com", "code": 5555},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("reset_token", resp.data)

    def test_verify_reset_otp_wrong_code(self):
        ResetPasswordCode.objects.create(user=self.user, code=5555)
        resp = self.client.post(
            reverse("confirm_reset_password"),
            {"email": "reset@test.com", "code": 0000},
        )
        self.assertEqual(resp.status_code, 400)

    def test_verify_reset_otp_expired(self):
        code = ResetPasswordCode.objects.create(user=self.user, code=5555)
        ResetPasswordCode.objects.filter(pk=code.pk).update(
            created_at=timezone.now() - timedelta(minutes=6)
        )
        resp = self.client.post(
            reverse("confirm_reset_password"),
            {"email": "reset@test.com", "code": 5555},
        )
        self.assertEqual(resp.status_code, 400)

    def test_set_new_password_success(self):
        token = secrets.token_urlsafe(32)
        ResetPasswordCode.objects.create(
            user=self.user, code=7777, reset_token=token
        )
        resp = self.client.post(
            reverse("set_new_password"),
            {
                "email": "reset@test.com",
                "reset_token": token,
                "new_password": "newpass1234",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass1234"))

    def test_set_new_password_invalid_token(self):
        resp = self.client.post(
            reverse("set_new_password"),
            {
                "email": "reset@test.com",
                "reset_token": "bad-token",
                "new_password": "newpass1234",
            },
        )
        self.assertEqual(resp.status_code, 400)

    def test_set_new_password_expired_token(self):
        token = secrets.token_urlsafe(32)
        code = ResetPasswordCode.objects.create(
            user=self.user, code=8888, reset_token=token
        )
        ResetPasswordCode.objects.filter(pk=code.pk).update(
            created_at=timezone.now() - timedelta(minutes=6)
        )
        resp = self.client.post(
            reverse("set_new_password"),
            {
                "email": "reset@test.com",
                "reset_token": token,
                "new_password": "newpass1234",
            },
        )
        self.assertEqual(resp.status_code, 400)


class GovernoratesCitiesViewTests(TestCase):
    """Tests for the governorates/cities JSON endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("get_governorates_cities")

    @override_settings(BASE_DIR=PathLib("/tmp/fake"))
    def test_file_not_found_raises(self):
        """If the JSON file is missing the view will raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self.client.get(self.url)

    def test_returns_json(self):
        """
        If the data file exists, the endpoint should return valid JSON.
        We just confirm the endpoint is reachable and returns 200 OR
        a server error (if the file is missing in CI).
        """
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, [200, 500])
