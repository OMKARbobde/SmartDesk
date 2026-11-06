from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import EmployeeProfile
from departments.models import Department
from tickets.models import Ticket
from .models import Assignment

User = get_user_model()


class AssignmentApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("assign-admin", password="test-pass", role="ADMIN")
        self.agent = User.objects.create_user("assign-agent", password="test-pass", role="AGENT")
        self.employee_user = User.objects.create_user("assign-employee", password="test-pass", role="EMPLOYEE")
        self.other_user = User.objects.create_user("assign-other", password="test-pass", role="EMPLOYEE")
        self.department = Department.objects.create(name="Support", code="SUP")
        self.employee = EmployeeProfile.objects.create(
            user=self.employee_user, employee_id="E-1", department=self.department,
            designation="Support", is_available=True,
        )
        self.other = EmployeeProfile.objects.create(
            user=self.other_user, employee_id="E-2", department=self.department,
            designation="Support", is_available=True,
        )
        self.ticket = Ticket.objects.create(
            ticket_id="SD-ASSIGN-1", title="Example", description="Example",
            created_by=self.employee_user, department=self.department,
        )
        self.client = APIClient()

    def post_assignment(self, profile_id=None):
        return self.client.post(
            f"/api/tickets/{self.ticket.pk}/assignments/",
            {"employee_profile_id": profile_id or self.employee.pk, "remarks": "handoff"},
            format="json",
        )

    def test_agent_can_create_assignment_and_response_is_enveloped(self):
        self.client.force_authenticate(self.agent)
        response = self.post_assignment()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["status"], "ASSIGNED")
        self.assertIn("Location", response)
        self.assertEqual(Assignment.objects.count(), 1)

    def test_reassignment_preserves_old_history_and_sets_actor(self):
        old = Assignment.objects.create(ticket=self.ticket, assigned_to=self.employee, assigned_by=self.admin)
        self.client.force_authenticate(self.agent)
        response = self.post_assignment(self.other.pk)
        self.assertEqual(response.status_code, 201)
        old.refresh_from_db()
        self.assertEqual(old.status, "REASSIGNED")
        current = Assignment.objects.get(status="ASSIGNED")
        self.assertEqual(current.assigned_to_id, self.other.pk)
        self.assertEqual(current.assigned_by_id, self.agent.pk)

    def test_duplicate_current_state_returns_conflict_without_mutation(self):
        first = Assignment.objects.create(ticket=self.ticket, assigned_to=self.employee)
        second = Assignment.objects.create(ticket=self.ticket, assigned_to=self.other)
        self.client.force_authenticate(self.agent)
        response = self.post_assignment(self.other.pk)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "conflict")
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.status, second.status), ("ASSIGNED", "ASSIGNED"))
        self.assertEqual(Assignment.objects.count(), 2)

    def test_unavailable_or_inactive_employee_cannot_be_assigned(self):
        self.client.force_authenticate(self.agent)
        self.employee.is_available = False
        self.employee.save(update_fields=["is_available"])
        response = self.post_assignment()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")
        self.employee.is_available = True
        self.employee.save(update_fields=["is_available"])
        self.employee_user.is_active = False
        self.employee_user.save(update_fields=["is_active"])
        response = self.post_assignment()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Assignment.objects.count(), 0)

    def test_employee_sees_only_own_assignments(self):
        own = Assignment.objects.create(ticket=self.ticket, assigned_to=self.employee)
        another_ticket = Ticket.objects.create(
            ticket_id="SD-ASSIGN-2", title="Other", description="Other",
            created_by=self.other_user, department=self.department,
        )
        Assignment.objects.create(ticket=another_ticket, assigned_to=self.other)
        self.client.force_authenticate(self.employee_user)
        response = self.client.get("/api/assignments/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["data"]], [own.pk])

    def test_employee_can_accept_then_complete_only_own_current_assignment(self):
        assignment = Assignment.objects.create(ticket=self.ticket, assigned_to=self.employee)
        self.client.force_authenticate(self.employee_user)
        response = self.client.patch(f"/api/assignments/{assignment.pk}/", {"status": "ACCEPTED"}, format="json")
        self.assertEqual(response.status_code, 200)
        response = self.client.patch(f"/api/assignments/{assignment.pk}/", {"status": "COMPLETED"}, format="json")
        self.assertEqual(response.status_code, 200)
        response = self.client.patch(f"/api/assignments/{assignment.pk}/", {"status": "REASSIGNED"}, format="json")
        # Once completed, the historical row is no longer visible to the
        # employee as a current assignment and cannot be mutated by them.
        self.assertEqual(response.status_code, 404)

    def test_employee_cannot_update_another_employees_assignment(self):
        assignment = Assignment.objects.create(ticket=self.ticket, assigned_to=self.other)
        self.client.force_authenticate(self.employee_user)
        response = self.client.patch(f"/api/assignments/{assignment.pk}/", {"status": "ACCEPTED"}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_invalid_assignment_payload_is_validation_error(self):
        self.client.force_authenticate(self.agent)
        response = self.client.post(f"/api/tickets/{self.ticket.pk}/assignments/", ["bad"], format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_employee_cannot_create_assignments(self):
        self.client.force_authenticate(self.employee_user)
        response = self.post_assignment()
        self.assertEqual(response.status_code, 403)

    def test_session_authenticated_assignment_write_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.agent)
        response = client.post(
            f"/api/tickets/{self.ticket.pk}/assignments/",
            {"employee_profile_id": self.employee.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "csrf_failed")
