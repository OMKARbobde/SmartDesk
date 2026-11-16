from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import EmployeeProfile, User
from assignment.models import Assignment
from assignment.services import assign_or_reassign, update_assignment_if_unchanged
from auditlog.models import AuditEvent
from departments.models import Department
from tickets.models import Ticket
from tickets.services import apply_bulk_ticket_update, update_ticket_if_unchanged

from .models import Notification


class NotificationApiAndWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("notify-admin", password="test-pass", role="ADMIN")
        self.agent = User.objects.create_user("notify-agent", password="test-pass", role="AGENT")
        self.creator = User.objects.create_user("notify-creator", password="test-pass", role="EMPLOYEE")
        self.first_assignee = User.objects.create_user("notify-first", password="test-pass", role="EMPLOYEE")
        self.second_assignee = User.objects.create_user("notify-second", password="test-pass", role="EMPLOYEE")
        self.department = Department.objects.create(name="Notification Operations", code="NOTIFY")
        self.first_profile = EmployeeProfile.objects.create(
            user=self.first_assignee, employee_id="NTFY-001", department=self.department,
            designation="Support Engineer",
        )
        self.second_profile = EmployeeProfile.objects.create(
            user=self.second_assignee, employee_id="NTFY-002", department=self.department,
            designation="Support Engineer",
        )
        self.ticket = Ticket.objects.create(
            ticket_id="SD-NOTIFY-001", title="Notification workflow", description="Fixture",
            created_by=self.creator, department=self.department,
        )
        self.client = APIClient()

    def test_assignment_create_and_reassignment_notify_relevant_users_once(self):
        assignment = assign_or_reassign(ticket=self.ticket, employee=self.first_profile, actor=self.admin)
        self.assertEqual(Notification.objects.filter(recipient=self.first_assignee).count(), 1)
        first = Notification.objects.get(recipient=self.first_assignee)
        self.assertEqual(first.notification_type, "ASSIGNMENT_CREATED")
        self.assertEqual(first.related_ticket_id, self.ticket.pk)
        self.assertEqual(first.related_assignment_id, assignment.pk)

        from .services import notify_assignment_created
        notify_assignment_created(assignment=assignment, actor=self.admin)
        self.assertEqual(Notification.objects.filter(recipient=self.first_assignee).count(), 1)

        reassigned = assign_or_reassign(ticket=self.ticket, employee=self.second_profile, actor=self.admin)
        self.assertEqual(Notification.objects.filter(notification_type="ASSIGNMENT_REASSIGNED").count(), 2)
        self.assertEqual(Notification.objects.filter(recipient=self.first_assignee, notification_type="ASSIGNMENT_REASSIGNED").count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.second_assignee, notification_type="ASSIGNMENT_REASSIGNED").count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.admin).count(), 0)
        self.assertEqual(Notification.objects.filter(related_assignment=reassigned).count(), 2)

    def test_ticket_status_and_bulk_status_changes_notify_creator_and_current_assignee(self):
        Assignment.objects.create(
            ticket=self.ticket, assigned_to=self.first_profile, assigned_by=self.admin, status="ASSIGNED"
        )
        stale = Ticket.objects.get(pk=self.ticket.pk)
        update_ticket_if_unchanged(stale, actor=self.agent, status="IN_PROGRESS")
        events = Notification.objects.filter(notification_type="TICKET_STATUS_CHANGED")
        self.assertEqual(events.count(), 2)
        self.assertSetEqual(set(events.values_list("recipient_id", flat=True)), {self.creator.pk, self.first_assignee.pk})
        self.assertEqual(events.filter(message__contains="In Progress").count(), 2)

        fresh = Ticket.objects.get(pk=self.ticket.pk)
        apply_bulk_ticket_update([fresh], field="status", value="RESOLVED", actor=self.admin)
        events = Notification.objects.filter(notification_type="TICKET_STATUS_CHANGED")
        self.assertEqual(events.count(), 4)
        self.assertEqual(events.filter(message__contains="Resolved").count(), 2)

    def test_assignment_acceptance_and_completion_notify_creator_and_assigner(self):
        assignment = Assignment.objects.create(
            ticket=self.ticket, assigned_to=self.first_profile, assigned_by=self.admin, status="ASSIGNED"
        )
        update_assignment_if_unchanged(assignment, actor=self.first_assignee, status="ACCEPTED")
        accepted = Notification.objects.filter(notification_type="ASSIGNMENT_ACCEPTED")
        self.assertEqual(accepted.count(), 2)
        self.assertSetEqual(set(accepted.values_list("recipient_id", flat=True)), {self.creator.pk, self.admin.pk})

        assignment.refresh_from_db()
        update_assignment_if_unchanged(assignment, actor=self.first_assignee, status="COMPLETED")
        completed = Notification.objects.filter(notification_type="ASSIGNMENT_COMPLETED")
        self.assertEqual(completed.count(), 2)
        self.assertSetEqual(set(completed.values_list("recipient_id", flat=True)), {self.creator.pk, self.admin.pk})

    def test_list_unread_count_mark_one_and_mark_all_are_recipient_scoped(self):
        one = Notification.objects.create(
            recipient=self.creator, notification_type="TICKET_STATUS_CHANGED", title="Status",
            message="Ticket status changed.", related_ticket=self.ticket, event_key="api-one",
        )
        two = Notification.objects.create(
            recipient=self.creator, notification_type="ASSIGNMENT_CREATED", title="Assigned",
            message="A ticket was assigned.", related_ticket=self.ticket, event_key="api-two",
        )
        other = Notification.objects.create(
            recipient=self.first_assignee, notification_type="TICKET_STATUS_CHANGED", title="Other",
            message="Another user's notification.", event_key="api-other",
        )
        self.client.force_authenticate(self.creator)
        response = self.client.get("/api/notifications/?page=1&page_size=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 1)
        self.assertEqual(response.json()["meta"]["pagination"]["count"], 2)
        self.assertTrue(response.json()["data"][0]["related_ticket"])

        response = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(response.json()["data"]["count"], 2)
        response = self.client.post(f"/api/notifications/{one.pk}/read/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["is_read"])
        self.assertEqual(self.client.get("/api/notifications/unread-count/").json()["data"]["count"], 1)

        response = self.client.post("/api/notifications/mark-all-read/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["updated_count"], 1)
        self.assertEqual(self.client.get("/api/notifications/unread-count/").json()["data"]["count"], 0)
        other.refresh_from_db()
        self.assertFalse(other.is_read)
        two.refresh_from_db()
        self.assertTrue(two.is_read)

    def test_cross_user_records_are_hidden_and_mutations_return_404(self):
        notification = Notification.objects.create(
            recipient=self.creator, notification_type="TICKET_STATUS_CHANGED", title="Private",
            message="Private to recipient.", event_key="private-row",
        )
        self.client.force_authenticate(self.first_assignee)
        self.assertEqual(self.client.get("/api/notifications/").json()["data"], [])
        self.assertEqual(self.client.get("/api/notifications/unread-count/").json()["data"]["count"], 0)
        response = self.client.post(f"/api/notifications/{notification.pk}/read/", {}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_unauthenticated_notification_requests_return_standard_401(self):
        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "not_authenticated")

    def test_notification_failure_rolls_back_assignment_and_audit_event(self):
        with patch("assignment.services.notify_assignment_created", side_effect=RuntimeError("notification failure")):
            with self.assertRaises(RuntimeError):
                assign_or_reassign(ticket=self.ticket, employee=self.first_profile, actor=self.admin)
        self.assertEqual(Assignment.objects.filter(ticket=self.ticket).count(), 0)
        self.assertEqual(AuditEvent.objects.count(), 0)
        self.assertEqual(Notification.objects.count(), 0)
