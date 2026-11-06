import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import EmployeeProfile, User
from assignment.models import Assignment
from assignment.services import assign_or_reassign, update_assignment_if_unchanged
from departments.models import Department
from tickets.models import Ticket
from tickets.services import (
    apply_bulk_ticket_update,
    archive_ticket,
    create_ticket,
    restore_ticket,
    update_ticket_if_unchanged,
)
from .admin import AuditEventAdmin
from .models import AuditEvent
from .services import record_event


class AuditEventApiTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            "audit-admin", password="test-pass", role="ADMIN", is_staff=True
        )
        self.agent = User.objects.create_user("audit-agent", password="test-pass", role="AGENT")
        self.employee_user = User.objects.create_user(
            "audit-employee", password="test-pass", role="EMPLOYEE"
        )
        self.other_employee_user = User.objects.create_user(
            "audit-other", password="test-pass", role="EMPLOYEE"
        )
        self.department = Department.objects.create(name="Audit Support", code="AUDIT")
        self.other_department = Department.objects.create(name="Audit Finance", code="AUFIN")
        self.employee = EmployeeProfile.objects.create(
            user=self.employee_user,
            employee_id="AUDIT-EMP-1",
            department=self.department,
            designation="Support Specialist",
        )
        self.other_employee = EmployeeProfile.objects.create(
            user=self.other_employee_user,
            employee_id="AUDIT-EMP-2",
            department=self.department,
            designation="Support Specialist",
        )
        self.ticket = self.make_ticket("SD-AUDIT-0001", created_by=self.employee_user)
        self.client = APIClient()

    def make_ticket(self, ticket_id, *, created_by=None, department=None, **values):
        return Ticket.objects.create(
            ticket_id=ticket_id,
            title="Example ticket",
            description="Example description",
            created_by=created_by or self.employee_user,
            department=department,
            **values,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user)

    def test_admin_can_read_events_but_agent_employee_and_anonymous_cannot(self):
        record_event(
            actor=self.admin_user,
            event_type="TICKET_STATUS_CHANGED",
            ticket=self.ticket,
            details={"from": "OPEN", "to": "IN_PROGRESS"},
        )
        response = self.client.get("/api/audit-logs/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "not_authenticated")

        for user in (self.agent, self.employee_user):
            with self.subTest(role=user.role):
                self.authenticate(user)
                response = self.client.get("/api/audit-logs/")
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], "permission_denied")

        self.authenticate(self.admin_user)
        response = self.client.get("/api/audit-logs/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["event_type"], "TICKET_STATUS_CHANGED")
        self.assertIn("pagination", response.json()["meta"])

    def test_audit_list_filters_and_stable_pagination(self):
        timestamp = timezone.now() - timedelta(days=1)
        with patch("django.db.models.fields.timezone.now", return_value=timestamp):
            first = record_event(
                actor=self.admin_user,
                event_type="TICKET_STATUS_CHANGED",
                ticket=self.ticket,
                details={"from": "OPEN", "to": "IN_PROGRESS"},
            )
            second = record_event(
                actor=self.agent,
                event_type="TICKET_PRIORITY_CHANGED",
                ticket=self.ticket,
                details={"from": "MEDIUM", "to": "HIGH"},
            )

        self.authenticate(self.admin_user)
        filtered = self.client.get(
            f"/api/audit-logs/?event_type=TICKET_STATUS_CHANGED&actor={self.admin_user.pk}"
            f"&ticket={self.ticket.pk}&created_after=2020-01-01T00:00:00Z"
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual([row["id"] for row in filtered.json()["data"]], [first.pk])

        page_one = self.client.get("/api/audit-logs/?page=1&page_size=1&ordering=created_at")
        page_two = self.client.get("/api/audit-logs/?page=2&page_size=1&ordering=created_at")
        self.assertEqual(page_one.status_code, 200)
        self.assertEqual(page_two.status_code, 200)
        ids = [page_one.json()["data"][0]["id"], page_two.json()["data"][0]["id"]]
        self.assertEqual(ids, sorted((first.pk, second.pk)))
        self.assertEqual(page_one.json()["meta"]["pagination"]["next"], 2)
        self.assertEqual(page_two.json()["meta"]["pagination"]["previous"], 1)

    def test_invalid_filters_use_standard_validation_envelope(self):
        self.authenticate(self.admin_user)
        for query in (
            "?event_type=UNSUPPORTED",
            "?actor=0",
            "?ticket=abc",
            "?page_size=101",
            "?created_after=2026-01-01T00:00:00",
            "?event_type=TICKET_CREATED&event_type=TICKET_UPDATED",
            "?created_after=2026-01-02T00:00:00Z&created_before=2026-01-01T00:00:00Z",
            "?unexpected=true",
        ):
            with self.subTest(query=query):
                response = self.client.get("/api/audit-logs/" + query)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "validation_error")
                self.assertIn("details", response.json()["error"])

    def test_endpoint_is_read_only(self):
        self.authenticate(self.admin_user)
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)("/api/audit-logs/", {}, format="json")
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.json()["error"]["code"], "method_not_allowed")

    def test_ticket_create_update_status_and_priority_events_are_safe(self):
        self.authenticate(self.admin_user)
        title = "Private title that must not be copied to the audit row"
        description = "Private description that must not be copied to the audit row"
        created = self.client.post(
            "/api/tickets/",
            {"title": title, "description": description, "department_id": self.department.pk},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        created_ticket = Ticket.objects.get(pk=created.json()["data"]["id"])
        create_event = AuditEvent.objects.get(ticket=created_ticket, event_type="TICKET_CREATED")
        self.assertEqual(create_event.actor_user_id_snapshot, self.admin_user.pk)
        self.assertEqual(create_event.details, {
            "status": "OPEN", "priority": "MEDIUM", "department_id": self.department.pk,
        })

        updated = self.client.patch(
            f"/api/tickets/{created_ticket.pk}/",
            {
                "title": "Replaced sensitive title",
                "description": "Replaced sensitive description",
                "department_id": self.other_department.pk,
                "status": "IN_PROGRESS",
                "priority": "HIGH",
                "expected_updated_at": created_ticket.updated_at.isoformat(),
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        events = list(AuditEvent.objects.filter(ticket=created_ticket).order_by("event_type"))
        self.assertEqual({event.event_type for event in events}, {
            "TICKET_CREATED", "TICKET_STATUS_CHANGED", "TICKET_PRIORITY_CHANGED", "TICKET_UPDATED",
        })
        generic = next(event for event in events if event.event_type == "TICKET_UPDATED")
        self.assertCountEqual(generic.details["changed_fields"], ["title", "description", "department_id"])
        self.assertEqual(generic.details["changes"]["department_id"], {
            "from": self.department.pk, "to": self.other_department.pk,
        })

        self.authenticate(self.admin_user)
        logs = self.client.get(f"/api/audit-logs/?ticket={created_ticket.pk}")
        self.assertEqual(logs.status_code, 200)
        serialized = json.dumps(logs.json())
        self.assertNotIn(title, serialized)
        self.assertNotIn(description, serialized)
        self.assertNotIn("password", serialized.lower())
        self.assertEqual(logs.json()["data"][0]["actor"]["id"], self.admin_user.pk)

    def test_bulk_status_and_priority_events_are_emitted_per_changed_ticket(self):
        first = self.make_ticket("SD-AUDIT-BULK-01", status="OPEN", priority="MEDIUM")
        second = self.make_ticket("SD-AUDIT-BULK-02", status="OPEN", priority="MEDIUM")
        self.authenticate(self.agent)
        status_response = self.client.post(
            "/api/tickets/bulk/",
            {"ticket_ids": [first.pk, second.pk], "action": "set_status", "value": "IN_PROGRESS"},
            format="json",
        )
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(AuditEvent.objects.filter(event_type="TICKET_BULK_STATUS_CHANGED").count(), 2)

        priority_response = self.client.post(
            "/api/tickets/bulk/",
            {"ticket_ids": [first.pk, second.pk], "action": "set_priority", "value": "HIGH"},
            format="json",
        )
        self.assertEqual(priority_response.status_code, 200)
        self.assertEqual(AuditEvent.objects.filter(event_type="TICKET_BULK_PRIORITY_CHANGED").count(), 2)

    def test_invalid_or_forbidden_ticket_actions_do_not_create_events(self):
        self.authenticate(self.agent)
        invalid = self.client.patch(
            f"/api/tickets/{self.ticket.pk}/",
            {"status": "CLOSED", "expected_updated_at": self.ticket.updated_at.isoformat()},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(AuditEvent.objects.count(), 0)

        self.authenticate(self.employee_user)
        forbidden = self.client.post(f"/api/tickets/{self.ticket.pk}/archive/", {}, format="json")
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_assignment_creation_reassignment_acceptance_and_completion(self):
        self.authenticate(self.agent)
        create = self.client.post(
            f"/api/tickets/{self.ticket.pk}/assignments/",
            {"employee_profile_id": self.employee.pk},
            format="json",
        )
        self.assertEqual(create.status_code, 201)
        first_assignment = Assignment.objects.get(pk=create.json()["data"]["id"])
        self.assertTrue(AuditEvent.objects.filter(
            event_type="ASSIGNMENT_CREATED", assignment=first_assignment,
            target_user=self.employee_user,
        ).exists())

        reassignment = self.client.post(
            f"/api/tickets/{self.ticket.pk}/assignments/",
            {"employee_profile_id": self.other_employee.pk},
            format="json",
        )
        self.assertEqual(reassignment.status_code, 201)
        first_assignment.refresh_from_db()
        current = Assignment.objects.get(pk=reassignment.json()["data"]["id"])
        self.assertEqual(first_assignment.status, "REASSIGNED")
        self.assertTrue(AuditEvent.objects.filter(
            event_type="ASSIGNMENT_REASSIGNED", assignment=current,
            target_user=self.other_employee_user,
        ).exists())

        self.authenticate(self.other_employee_user)
        accepted = self.client.patch(
            f"/api/assignments/{current.pk}/", {"status": "ACCEPTED"}, format="json"
        )
        self.assertEqual(accepted.status_code, 200)
        completed = self.client.patch(
            f"/api/assignments/{current.pk}/", {"status": "COMPLETED"}, format="json"
        )
        self.assertEqual(completed.status_code, 200)
        self.assertTrue(AuditEvent.objects.filter(
            event_type="ASSIGNMENT_ACCEPTED", assignment=current, actor=self.other_employee_user
        ).exists())
        self.assertTrue(AuditEvent.objects.filter(
            event_type="ASSIGNMENT_COMPLETED", assignment=current, actor=self.other_employee_user
        ).exists())

    def test_archive_restore_and_repeated_actions_are_idempotent_in_audit(self):
        self.authenticate(self.agent)
        archived = self.client.post(f"/api/tickets/{self.ticket.pk}/archive/", {}, format="json")
        self.assertEqual(archived.status_code, 200)
        self.client.post(f"/api/tickets/{self.ticket.pk}/archive/", {}, format="json")
        self.assertEqual(AuditEvent.objects.filter(event_type="TICKET_ARCHIVED").count(), 1)

        self.authenticate(self.admin_user)
        restored = self.client.post(f"/api/tickets/{self.ticket.pk}/restore/", {}, format="json")
        self.assertEqual(restored.status_code, 200)
        self.client.post(f"/api/tickets/{self.ticket.pk}/restore/", {}, format="json")
        self.assertEqual(AuditEvent.objects.filter(event_type="TICKET_RESTORED").count(), 1)

    def test_optional_related_rows_can_be_removed_without_deleting_audit_event(self):
        event = record_event(
            actor=self.admin_user,
            event_type="TICKET_STATUS_CHANGED",
            ticket=self.ticket,
            details={"from": "OPEN", "to": "IN_PROGRESS"},
        )
        ticket_pk, public_id = self.ticket.pk, self.ticket.ticket_id
        self.ticket.delete()
        event.refresh_from_db()
        self.assertIsNone(event.ticket)
        self.assertEqual(event.ticket_pk_snapshot, ticket_pk)
        self.assertEqual(event.ticket_public_id_snapshot, public_id)
        self.assertTrue(AuditEvent.objects.filter(pk=event.pk).exists())

    def test_model_and_admin_reject_event_edits_and_deletes(self):
        event = record_event(
            actor=self.admin_user,
            event_type="TICKET_STATUS_CHANGED",
            ticket=self.ticket,
            details={"from": "OPEN", "to": "IN_PROGRESS"},
        )
        event.details = {"description": "attempted overwrite"}
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()

        model_admin = AuditEventAdmin(AuditEvent, admin.site)
        request = type("Request", (), {"user": self.admin_user})()
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))
        self.assertTrue(model_admin.has_view_permission(request))
        agent_request = type("Request", (), {"user": self.agent})()
        self.assertFalse(model_admin.has_view_permission(agent_request))
        with self.assertRaises(ValidationError):
            AuditEvent.objects.filter(pk=event.pk).update(event_type="TICKET_CREATED")
        with self.assertRaises(ValidationError):
            AuditEvent.objects.filter(pk=event.pk).delete()


class AuditEventAtomicityTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user("atomic-admin", password="test-pass", role="ADMIN")
        self.agent = User.objects.create_user("atomic-agent", password="test-pass", role="AGENT")
        self.employee_user = User.objects.create_user("atomic-employee", password="test-pass", role="EMPLOYEE")
        self.other_user = User.objects.create_user("atomic-other", password="test-pass", role="EMPLOYEE")
        self.department = Department.objects.create(name="Atomic Support", code="ATOM")
        self.employee = EmployeeProfile.objects.create(
            user=self.employee_user, employee_id="ATOM-1", department=self.department,
            designation="Support Specialist",
        )
        self.other_employee = EmployeeProfile.objects.create(
            user=self.other_user, employee_id="ATOM-2", department=self.department,
            designation="Support Specialist",
        )
        self.ticket = Ticket.objects.create(
            ticket_id="SD-ATOMIC-1", title="Before", description="No audit failure data leak",
            created_by=self.employee_user, status="OPEN", priority="MEDIUM",
        )

    def test_ticket_creation_rolls_back_if_audit_write_fails(self):
        with patch("tickets.services.record_ticket_created", side_effect=RuntimeError("audit failure")):
            with self.assertRaises(RuntimeError):
                create_ticket(created_by=self.admin_user, title="Atomic", description="Test")
        self.assertFalse(Ticket.objects.filter(title="Atomic").exists())
        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_ticket_update_rolls_back_if_audit_write_fails(self):
        before_timestamp = self.ticket.updated_at
        with patch("tickets.services.record_ticket_changes", side_effect=RuntimeError("audit failure")):
            with self.assertRaises(RuntimeError):
                update_ticket_if_unchanged(self.ticket, actor=self.agent, title="After")
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.title, "Before")
        self.assertEqual(self.ticket.updated_at, before_timestamp)
        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_bulk_update_rolls_back_prior_tickets_and_events_if_later_audit_fails(self):
        second = Ticket.objects.create(
            ticket_id="SD-ATOMIC-2", title="Before two", description="Test",
            created_by=self.employee_user, status="OPEN", priority="MEDIUM",
        )
        original = __import__("tickets.services", fromlist=["record_bulk_ticket_update"]).record_bulk_ticket_update
        calls = {"count": 0}

        def fail_second(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("audit failure")
            return original(*args, **kwargs)

        with patch("tickets.services.record_bulk_ticket_update", side_effect=fail_second):
            with self.assertRaises(RuntimeError):
                apply_bulk_ticket_update([self.ticket, second], field="priority", value="HIGH", actor=self.agent)
        self.ticket.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((self.ticket.priority, second.priority), ("MEDIUM", "MEDIUM"))
        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_archive_and_restore_roll_back_if_audit_write_fails(self):
        with patch("tickets.services.record_ticket_archived", side_effect=RuntimeError("audit failure")):
            with self.assertRaises(RuntimeError):
                archive_ticket(self.ticket, actor=self.agent)
        self.ticket.refresh_from_db()
        self.assertFalse(self.ticket.is_archived)

        Ticket.objects.filter(pk=self.ticket.pk).update(is_archived=True)
        self.ticket.refresh_from_db()
        with patch("tickets.services.record_ticket_restored", side_effect=RuntimeError("audit failure")):
            with self.assertRaises(RuntimeError):
                restore_ticket(self.ticket, actor=self.admin_user)
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.is_archived)
        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_assignment_create_reassign_and_status_change_roll_back_on_audit_failure(self):
        with patch("assignment.services.record_assignment_created", side_effect=RuntimeError("audit failure")):
            with self.assertRaises(RuntimeError):
                assign_or_reassign(ticket=self.ticket, employee=self.employee, actor=self.agent)
        self.assertEqual(Assignment.objects.count(), 0)

        previous = Assignment.objects.create(
            ticket=self.ticket, assigned_to=self.employee, assigned_by=self.agent, status="ASSIGNED"
        )
        with patch("assignment.services.record_assignment_reassigned", side_effect=RuntimeError("audit failure")):
            with self.assertRaises(RuntimeError):
                assign_or_reassign(ticket=self.ticket, employee=self.other_employee, actor=self.agent)
        previous.refresh_from_db()
        self.assertEqual(previous.status, "ASSIGNED")
        self.assertEqual(Assignment.objects.count(), 1)

        with patch("assignment.services.record_assignment_status_change", side_effect=RuntimeError("audit failure")):
            with self.assertRaises(RuntimeError):
                update_assignment_if_unchanged(previous, actor=self.employee_user, status="ACCEPTED")
        previous.refresh_from_db()
        self.assertEqual(previous.status, "ASSIGNED")
        self.assertEqual(AuditEvent.objects.count(), 0)
