from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from departments.models import Department
from .models import EmployeeProfile
from .permissions import IsAdmin, IsAdminOrAgent, IsSmartDeskUser


User = get_user_model()


class AuthenticationApiTests(TestCase):
    password = "test-password-not-for-production"

    def setUp(self):
        self.user = User.objects.create_user(
            username="taylor",
            email="taylor@example.test",
            password=self.password,
            first_name="Taylor",
            last_name="Morgan",
            role="EMPLOYEE",
        )
        self.client = APIClient(enforce_csrf_checks=True)

    def bootstrap_csrf(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", self.client.cookies)
        return response.json()["data"]["csrf_token"]

    def login(self, identifier="taylor"):
        initial_token = self.bootstrap_csrf()
        response = self.client.post(
            "/api/auth/login/",
            {"identifier": identifier, "password": self.password},
            format="json",
            HTTP_X_CSRFTOKEN=initial_token,
        )
        return response, initial_token

    def test_csrf_bootstrap_sets_cookie_and_returns_token(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.cookies["csrftoken"].value)
        self.assertTrue(response.json()["data"]["csrf_token"])
        self.assertEqual(response.json()["meta"], {})

    def test_anonymous_login_requires_csrf_and_returns_json_error(self):
        response = self.client.post(
            "/api/auth/login/",
            {"identifier": "taylor", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "csrf_failed")
        self.assertEqual(response.json()["error"]["details"], {})

    def test_login_by_username_rotates_csrf_token_and_returns_safe_user(self):
        initial_token = self.bootstrap_csrf()
        initial_cookie = self.client.cookies["csrftoken"].value
        response = self.client.post(
            "/api/auth/login/",
            {"identifier": "taylor", "password": self.password},
            format="json",
            HTTP_X_CSRFTOKEN=initial_token,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("data", body)
        self.assertIn("meta", body)
        self.assertNotEqual(body["meta"]["csrf_token"], initial_token)
        self.assertNotEqual(self.client.cookies["csrftoken"].value, initial_cookie)
        self.assertEqual(body["data"]["user"]["username"], "taylor")
        self.assertNotIn("password", body["data"]["user"])

    def test_login_by_unique_email(self):
        response, _ = self.login("TAYLOR@example.test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["user"]["id"], self.user.pk)

    def test_ambiguous_email_is_rejected_without_logging_in(self):
        User.objects.create_user(
            username="another",
            email="taylor@example.test",
            password=self.password,
            role="AGENT",
        )
        token = self.bootstrap_csrf()
        response = self.client.post(
            "/api/auth/login/",
            {"identifier": "taylor@example.test", "password": self.password},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "ambiguous_identifier")
        self.assertNotIn("taylor@example.test", response.content.decode())
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_invalid_credentials_use_authentication_error_envelope(self):
        token = self.bootstrap_csrf()
        response = self.client.post(
            "/api/auth/login/",
            {"identifier": "taylor", "password": "incorrect"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "authentication_failed")
        self.assertEqual(response.json()["error"]["details"], {})

    def test_unauthenticated_current_user_returns_json_401(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "not_authenticated")

    def test_current_user_does_not_expose_password_or_sensitive_fields(self):
        response, _ = self.login()
        self.assertEqual(response.status_code, 200)
        profile = self.client.get("/api/auth/me/")
        self.assertEqual(profile.status_code, 200)
        user_data = profile.json()["data"]["user"]
        self.assertEqual(
            set(user_data),
            {"id", "username", "email", "first_name", "last_name", "display_name", "role", "employee_profile_id"},
        )
        self.assertNotIn("password", profile.content.decode().lower())
        self.assertNotIn("is_superuser", user_data)
        self.assertNotIn("user_permissions", user_data)

    def test_logout_requires_csrf_and_ends_session_when_valid(self):
        login_response, _ = self.login()
        token = login_response.json()["meta"]["csrf_token"]

        rejected = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(rejected.json()["error"]["code"], "csrf_failed")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

        logged_out = self.client.post(
            "/api/auth/logout/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(logged_out.status_code, 204)
        self.assertEqual(logged_out.content, b"")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_profile_patch_requires_csrf_and_rejects_role_changes(self):
        login_response, _ = self.login()
        token = login_response.json()["meta"]["csrf_token"]

        rejected = self.client.patch(
            "/api/users/me/",
            {"first_name": "Changed"},
            format="json",
        )
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(rejected.json()["error"]["code"], "csrf_failed")

        forbidden_field = self.client.patch(
            "/api/users/me/",
            {"role": "ADMIN"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(forbidden_field.status_code, 400)
        self.assertEqual(forbidden_field.json()["error"]["code"], "validation_error")
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, "EMPLOYEE")

        updated = self.client.patch(
            "/api/users/me/",
            {"first_name": "Updated"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["user"]["first_name"], "Updated")

    def test_profile_patch_rejects_duplicate_email(self):
        User.objects.create_user(username="existing", email="taken@example.test", password=self.password)
        login_response, _ = self.login()
        token = login_response.json()["meta"]["csrf_token"]
        response = self.client.patch(
            "/api/users/me/",
            {"email": "TAKEN@example.test"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")


class RolePermissionFoundationTests(TestCase):
    def make_user(self, role):
        return User.objects.create_user(
            username=role.lower(),
            password="test-password-not-for-production",
            role=role,
        )

    def test_role_permissions_allow_only_intended_roles(self):
        admin = self.make_user("ADMIN")
        agent = self.make_user("AGENT")
        employee = self.make_user("EMPLOYEE")

        self.assertTrue(IsAdmin().has_permission(SimpleNamespace(user=admin), None))
        self.assertFalse(IsAdmin().has_permission(SimpleNamespace(user=agent), None))
        self.assertTrue(IsAdminOrAgent().has_permission(SimpleNamespace(user=agent), None))
        self.assertFalse(IsAdminOrAgent().has_permission(SimpleNamespace(user=employee), None))
        self.assertTrue(IsSmartDeskUser().has_permission(SimpleNamespace(user=employee), None))


class EmployeeApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("employee-admin", password="test-pass", role="ADMIN")
        self.agent = User.objects.create_user("employee-agent", password="test-pass", role="AGENT")
        self.employee_user = User.objects.create_user(
            "employee-self", password="test-pass", role="EMPLOYEE", first_name="Alex", last_name="Morgan",
            email="alex@example.test",
        )
        self.other_user = User.objects.create_user("employee-other", password="test-pass", role="EMPLOYEE")
        self.department = Department.objects.create(name="Employee Support", code="ESUP")
        self.profile = EmployeeProfile.objects.create(
            user=self.employee_user, employee_id="EMP-A", department=self.department, designation="Analyst"
        )
        self.other_profile = EmployeeProfile.objects.create(
            user=self.other_user, employee_id="EMP-B", department=self.department, designation="Technician"
        )
        self.client = APIClient()

    def test_directory_search_department_filter_and_pagination(self):
        self.client.force_authenticate(self.agent)
        response = self.client.get("/api/employees/?search=Alex&department=%s&page_size=1" % self.department.pk)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]), 1)
        self.assertEqual(body["data"][0]["id"], self.profile.pk)
        self.assertEqual(body["meta"]["pagination"]["count"], 1)

    def test_employee_directory_is_for_admin_and_agent(self):
        self.client.force_authenticate(self.employee_user)
        response = self.client.get("/api/employees/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "permission_denied")

    def test_employee_can_read_self_but_not_another_profile(self):
        self.client.force_authenticate(self.employee_user)
        own = self.client.get(f"/api/employees/{self.profile.pk}/")
        other = self.client.get(f"/api/employees/{self.other_profile.pk}/")
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.json()["data"]["display_name"], "Alex Morgan")
        self.assertEqual(other.status_code, 403)

    def test_self_service_can_only_change_phone_and_sensitive_fields_are_absent(self):
        self.client.force_authenticate(self.employee_user)
        response = self.client.patch(
            f"/api/employees/{self.profile.pk}/", {"phone_number": "1234567"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["phone_number"], "1234567")
        self.assertNotIn("password", response.json()["data"])
        denied = self.client.patch(
            f"/api/employees/{self.profile.pk}/", {"is_available": False}, format="json"
        )
        self.assertEqual(denied.status_code, 400)

    def test_admin_can_edit_workforce_fields_but_not_user_role(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/employees/{self.profile.pk}/", {"is_available": False, "designation": "Senior Analyst"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        denied = self.client.patch(f"/api/employees/{self.profile.pk}/", {"role": "ADMIN"}, format="json")
        self.assertEqual(denied.status_code, 400)
        self.employee_user.refresh_from_db()
        self.assertEqual(self.employee_user.role, "EMPLOYEE")
