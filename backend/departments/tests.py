from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import EmployeeProfile
from assignment.models import Assignment
from tickets.models import Ticket
from .models import Department

User = get_user_model()


class DepartmentApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("dept-admin", password="test-pass", role="ADMIN")
        self.employee = User.objects.create_user("dept-employee", password="test-pass", role="EMPLOYEE")
        self.active = Department.objects.create(name="Active", code="ACT", is_active=True)
        self.inactive = Department.objects.create(name="Inactive", code="INA", is_active=False)
        self.client = APIClient()

    def test_active_departments_visible_to_authenticated_user(self):
        self.client.force_authenticate(self.employee)
        response = self.client.get("/api/departments/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.json()["data"]], [self.active.id])

    def test_admin_can_explicitly_include_inactive_departments(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/departments/?include_inactive=true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 2)

    def test_non_admin_cannot_request_inactive_departments(self):
        self.client.force_authenticate(self.employee)
        response = self.client.get("/api/departments/?include_inactive=true")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "permission_denied")

    def test_malformed_filter_uses_validation_envelope(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/departments/?include_inactive=maybe")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")


class DepartmentAnalyticsApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("analytics-admin", password="test-pass", role="ADMIN")
        self.agent = User.objects.create_user("analytics-agent", password="test-pass", role="AGENT")
        self.employee = User.objects.create_user("analytics-employee", password="test-pass", role="EMPLOYEE")
        self.outsider = User.objects.create_user("analytics-outsider", password="test-pass", role="EMPLOYEE")
        self.alpha = Department.objects.create(name="Alpha", code="ALPHA")
        self.beta = Department.objects.create(name="Beta", code="BETA")
        self.empty = Department.objects.create(name="Empty", code="EMPTY")
        self.profile = EmployeeProfile.objects.create(
            user=self.employee,
            employee_id="AN-EMP-1",
            department=self.alpha,
            designation="Support Engineer",
        )
        self.own_open = self.make_ticket(
            "SD-AN-001", self.employee, self.alpha, "OPEN", "HIGH"
        )
        self.assigned_resolved = self.make_ticket(
            "SD-AN-002", self.agent, self.beta, "RESOLVED", "CRITICAL"
        )
        Assignment.objects.create(
            ticket=self.assigned_resolved,
            assigned_to=self.profile,
            assigned_by=self.agent,
            status="ACCEPTED",
        )
        self.unrelated_open = self.make_ticket(
            "SD-AN-003", self.outsider, self.beta, "OPEN", "LOW"
        )
        self.closed = self.make_ticket(
            "SD-AN-004", self.admin, self.alpha, "CLOSED", "MEDIUM"
        )
        self.unassigned = self.make_ticket(
            "SD-AN-005", self.admin, None, "OPEN", "HIGH"
        )
        self.archived = self.make_ticket(
            "SD-AN-006", self.employee, self.alpha, "IN_PROGRESS", "MEDIUM", is_archived=True
        )

    @staticmethod
    def make_ticket(ticket_id, creator, department, status, priority, is_archived=False):
        return Ticket.objects.create(
            ticket_id=ticket_id,
            title=ticket_id,
            description="Analytics fixture ticket",
            created_by=creator,
            department=department,
            status=status,
            priority=priority,
            is_archived=is_archived,
        )

    def client_for(self, user):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client

    def get_analytics(self, user, query=""):
        return self.client_for(user).get(f"/api/analytics/departments/{query}")

    def test_admin_and_agent_get_department_counts_and_priority_distribution(self):
        for user in (self.admin, self.agent):
            with self.subTest(role=user.role):
                response = self.get_analytics(user)
                self.assertEqual(response.status_code, 200)
                body = response.json()["data"]
                summary = body["summary"]
                self.assertEqual(summary["total_tickets"], 5)
                self.assertEqual(summary["status_counts"], {
                    "OPEN": 3, "IN_PROGRESS": 0, "RESOLVED": 1, "CLOSED": 1,
                })
                self.assertEqual(summary["priority_counts"], {
                    "LOW": 1, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 1,
                })
                self.assertEqual(summary["workload_count"], 3)
                self.assertEqual(sum(summary["status_counts"].values()), summary["total_tickets"])
                self.assertEqual(sum(summary["priority_counts"].values()), summary["total_tickets"])

                rows = {row["department"]["name"] if row["department"] else None: row
                        for row in body["departments"]}
                self.assertEqual(rows["Alpha"]["total_tickets"], 2)
                self.assertEqual(rows["Beta"]["total_tickets"], 2)
                self.assertEqual(rows["Empty"]["total_tickets"], 0)
                self.assertEqual(rows[None]["total_tickets"], 1)
                self.assertEqual(rows["Beta"]["priority_counts"]["CRITICAL"], 1)

    def test_employee_analytics_use_only_created_or_currently_assigned_visible_tickets(self):
        # A creator can also be an assignee. Duplicate join rows must not
        # inflate ticket totals or enum breakdowns.
        Assignment.objects.create(
            ticket=self.own_open,
            assigned_to=self.profile,
            assigned_by=self.agent,
            status="ASSIGNED",
        )
        response = self.get_analytics(self.employee)
        self.assertEqual(response.status_code, 200)
        body = response.json()["data"]
        self.assertEqual(body["summary"]["total_tickets"], 2)
        rows = {row["department"]["name"]: row for row in body["departments"] if row["department"]}
        self.assertEqual(rows["Alpha"]["total_tickets"], 1)
        self.assertEqual(rows["Beta"]["total_tickets"], 1)
        self.assertEqual(body["summary"]["status_counts"]["IN_PROGRESS"], 0)

    def test_archived_tickets_are_excluded_from_every_aggregate(self):
        response = self.get_analytics(self.admin)
        self.assertEqual(response.status_code, 200)
        body = response.json()["data"]
        self.assertEqual(body["summary"]["total_tickets"], 5)
        self.assertEqual(body["summary"]["status_counts"]["IN_PROGRESS"], 0)
        alpha = next(row for row in body["departments"] if row["department"] and row["department"]["id"] == self.alpha.id)
        self.assertEqual(alpha["total_tickets"], 2)
        self.assertEqual(alpha["priority_counts"]["MEDIUM"], 1)

    def test_department_and_date_filters_apply_to_ticket_membership(self):
        base = timezone.now().replace(microsecond=0)
        Ticket.objects.filter(pk=self.own_open.pk).update(created_at=base)
        Ticket.objects.filter(pk=self.assigned_resolved.pk).update(created_at=base + timedelta(seconds=1))
        Ticket.objects.filter(pk=self.unrelated_open.pk).update(created_at=base + timedelta(seconds=2))
        Ticket.objects.filter(pk=self.closed.pk).update(created_at=base - timedelta(days=5))

        after = base.isoformat().replace("+00:00", "Z")
        before = (base + timedelta(seconds=2)).isoformat().replace("+00:00", "Z")
        response = self.get_analytics(
            self.admin,
            f"?department={self.beta.id}&created_after={after}&created_before={before}",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["data"]
        self.assertEqual(body["summary"]["total_tickets"], 1)
        self.assertEqual(body["summary"]["status_counts"]["RESOLVED"], 1)
        self.assertEqual(len(body["departments"]), 1)
        self.assertEqual(body["departments"][0]["department"]["id"], self.beta.id)

    def test_resolution_time_is_explicitly_unavailable(self):
        response = self.get_analytics(self.admin)
        summary = response.json()["data"]["summary"]
        self.assertIsNone(summary["average_resolution_time_seconds"])
        self.assertFalse(summary["resolution_time_available"])
        self.assertIn("resolved_at", summary["resolution_time_unavailable_reason"])
        for row in response.json()["data"]["departments"]:
            self.assertIsNone(row["average_resolution_time_seconds"])
            self.assertFalse(row["resolution_time_available"])

    def test_unauthenticated_requests_return_standard_json_401(self):
        response = self.get_analytics(None)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "not_authenticated")

    def test_invalid_analytics_filters_use_standard_validation_envelope(self):
        for query in ("?department=0", "?created_after=2026-01-01T00:00:00", "?unknown=value"):
            with self.subTest(query=query):
                response = self.get_analytics(self.admin, query)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_date_range_must_be_increasing(self):
        response = self.get_analytics(
            self.admin,
            "?created_after=2026-02-01T00:00:00Z&created_before=2026-01-01T00:00:00Z",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("created_before", response.json()["error"]["details"])
