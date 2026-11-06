from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

from accounts.models import EmployeeProfile
from ai_engine.models import TicketAnalysis
from assignment.models import Assignment
from departments.models import Department
from smartdesk.api import Conflict
from tickets.models import Ticket
from tickets.permissions import (
    TicketVisibilityPermission,
    can_transition_ticket_status,
    visible_tickets_for,
)
from tickets.services import archive_ticket, update_ticket_if_unchanged


User = get_user_model()


class TicketVisibilityTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Platform", code="PLAT")
        self.other_department = Department.objects.create(name="Workplace", code="WORK")
        self.admin = self.make_user("admin-user", "ADMIN")
        self.agent = self.make_user("agent-user", "AGENT")
        self.employee = self.make_user("employee-user", "EMPLOYEE")
        self.other_employee = self.make_user("other-user", "EMPLOYEE")
        self.employee_profile = self.make_profile(self.employee, "EMP-001")
        self.other_profile = self.make_profile(self.other_employee, "EMP-002")

        self.created = self.make_ticket("SD-1001", "Created ticket", self.employee)
        self.assigned = self.make_ticket("SD-1002", "Assigned ticket", self.agent)
        self.completed_only = self.make_ticket("SD-1003", "Completed ticket", self.agent)
        self.unrelated = self.make_ticket("SD-1004", "Unrelated ticket", self.other_employee)
        self.cross_department = self.make_ticket(
            "SD-1005", "Other department ticket", self.other_employee, self.other_department
        )
        self.make_assignment(self.assigned, self.employee_profile, "ASSIGNED")
        self.make_assignment(self.completed_only, self.employee_profile, "COMPLETED")

    @staticmethod
    def make_user(username, role):
        return User.objects.create_user(username=username, password="unit-test-password", role=role)

    def make_profile(self, user, employee_id):
        return EmployeeProfile.objects.create(
            user=user,
            employee_id=employee_id,
            department=self.department,
            designation="Support Engineer",
        )

    def make_ticket(self, ticket_id, title, creator, department=None, status="OPEN"):
        return Ticket.objects.create(
            ticket_id=ticket_id,
            title=title,
            description=f"Description for {title}",
            created_by=creator,
            department=department or self.department,
            status=status,
        )

    @staticmethod
    def make_assignment(ticket, profile, assignment_status):
        return Assignment.objects.create(
            ticket=ticket,
            assigned_to=profile,
            status=assignment_status,
        )

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_visibility_helper_role_matrix(self):
        all_ids = set(Ticket.objects.values_list("pk", flat=True))
        self.assertSetEqual(set(visible_tickets_for(self.admin).values_list("pk", flat=True)), all_ids)
        self.assertSetEqual(set(visible_tickets_for(self.agent).values_list("pk", flat=True)), all_ids)
        self.assertSetEqual(
            set(visible_tickets_for(self.employee).values_list("pk", flat=True)),
            {self.created.pk, self.assigned.pk},
        )

    def test_object_permission_uses_the_same_visibility_policy(self):
        permission = TicketVisibilityPermission()
        request = type("Request", (), {"user": self.employee})()
        self.assertTrue(permission.has_object_permission(request, None, self.assigned))
        self.assertFalse(permission.has_object_permission(request, None, self.unrelated))

    def test_ticket_list_scopes_before_count_and_pagination(self):
        response = self.client_for(self.employee).get("/api/tickets/?page_size=1")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["meta"]["pagination"]["count"], 2)
        self.assertEqual(body["meta"]["pagination"]["total_pages"], 2)
        self.assertEqual({row["id"] for row in body["data"]} & {self.unrelated.pk, self.completed_only.pk}, set())

    def test_admin_and_agent_lists_are_cross_department(self):
        for user in (self.admin, self.agent):
            with self.subTest(role=user.role):
                response = self.client_for(user).get("/api/tickets/")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["meta"]["pagination"]["count"], 5)

    def test_out_of_scope_ticket_detail_is_404(self):
        response = self.client_for(self.employee).get(f"/api/tickets/{self.unrelated.pk}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_search_filters_and_stable_pagination(self):
        timestamp = timezone.now()
        first = self.make_ticket("SD-2001", "stable needle first", self.agent)
        second = self.make_ticket("SD-2002", "stable needle second", self.agent)
        Ticket.objects.filter(pk__in=[first.pk, second.pk]).update(created_at=timestamp)
        client = self.client_for(self.agent)
        first_page = client.get("/api/tickets/?search=needle&ordering=created_at&page_size=1")
        second_page = client.get("/api/tickets/?search=needle&ordering=created_at&page=2&page_size=1")
        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(first_page.json()["meta"]["pagination"]["count"], 2)
        self.assertEqual(first_page.json()["meta"]["pagination"]["next"], 2)
        self.assertEqual(first_page.json()["data"][0]["id"], first.pk)
        self.assertEqual(second_page.json()["data"][0]["id"], second.pk)
        self.assertEqual(second_page.json()["meta"]["pagination"]["previous"], 1)

    def test_department_status_priority_and_date_filters(self):
        query = (
            f"/api/tickets/?department={self.other_department.pk}"
            "&status=OPEN&priority=MEDIUM&created_after=2020-01-01T00:00:00Z"
        )
        response = self.client_for(self.agent).get(query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.json()["data"]], [self.cross_department.pk])
        invalid_date = self.client_for(self.agent).get("/api/tickets/?created_after=2020-01-01T00:00:00")
        self.assertEqual(invalid_date.status_code, 400)

    def test_filter_validation_and_out_of_range_page(self):
        client = self.client_for(self.admin)
        invalid = client.get("/api/tickets/?status=OPEN,INVALID")
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["error"]["code"], "validation_error")
        invalid_order = client.get("/api/tickets/?ordering=created_by")
        self.assertEqual(invalid_order.status_code, 400)
        out_of_range = client.get("/api/tickets/?page=8&page_size=100")
        self.assertEqual(out_of_range.status_code, 200)
        self.assertEqual(out_of_range.json()["data"], [])
        self.assertEqual(out_of_range.json()["meta"]["pagination"]["total_pages"], 1)

    def test_empty_result_has_zero_total_pages(self):
        response = self.client_for(self.admin).get("/api/tickets/?search=no-such-ticket")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["meta"]["pagination"]["total_pages"], 0)

    def test_create_generates_collision_safe_public_id(self):
        Ticket.objects.create(
            ticket_id="SD-COLLISION",
            title="Existing",
            description="Existing",
            created_by=self.admin,
        )
        with patch(
            "tickets.services.generate_public_ticket_id",
            side_effect=["SD-COLLISION", "SD-UNIQUE-001"],
        ):
            response = self.client_for(self.employee).post(
                "/api/tickets/",
                {"title": "New issue", "description": "A complete description."},
                format="json",
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["ticket_id"], "SD-UNIQUE-001")
        self.assertEqual(Ticket.objects.get(ticket_id="SD-UNIQUE-001").created_by, self.employee)

    def test_create_rejects_client_supplied_public_id_and_creator(self):
        response = self.client_for(self.admin).post(
            "/api/tickets/",
            {"ticket_id": "SD-FORGED", "created_by": self.other_employee.pk,
             "title": "Issue", "description": "Description"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")
        self.assertFalse(Ticket.objects.filter(ticket_id="SD-FORGED").exists())

    def test_non_object_payloads_return_validation_errors_for_ticket_writes(self):
        client = self.client_for(self.admin)
        ticket = self.make_ticket("SD-1010", "Malformed payload target", self.admin)
        endpoints = (
            ("POST", "/api/tickets/"),
            ("PATCH", f"/api/tickets/{ticket.pk}/"),
            ("POST", "/api/tickets/bulk/"),
        )
        payloads = ("null", "[]", "[{}]", '"text"', "42")
        for method, path in endpoints:
            for payload in payloads:
                with self.subTest(method=method, path=path, payload=payload):
                    response = client.generic(method, path, payload, content_type="application/json")
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_authenticated_ticket_creation_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin)
        response = client.post(
            "/api/tickets/",
            {"title": "CSRF protected", "description": "Unsafe request without a token."},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "csrf_failed")
        self.assertFalse(Ticket.objects.filter(title="CSRF protected").exists())

    def test_employee_cannot_edit_priority_or_department(self):
        self.created.refresh_from_db()
        response = self.client_for(self.employee).patch(
            f"/api/tickets/{self.created.pk}/",
            {"priority": "HIGH", "expected_updated_at": self.created.updated_at.isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")


    def patch_status(self, user, ticket, new_status):
        ticket.refresh_from_db()
        return self.client_for(user).patch(
            f"/api/tickets/{ticket.pk}/",
            {"status": new_status, "expected_updated_at": ticket.updated_at.isoformat()},
            format="json",
        )

    def test_admin_can_transition_any_status(self):
        ticket = self.make_ticket("SD-3001", "Closed issue", self.agent, status="CLOSED")
        response = self.patch_status(self.admin, ticket, "OPEN")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "OPEN")

    def test_agent_allowed_and_forbidden_transitions(self):
        allowed = self.make_ticket("SD-3002", "Open issue", self.admin, status="OPEN")
        rejected = self.make_ticket("SD-3003", "Closed issue", self.admin, status="CLOSED")
        self.assertEqual(self.patch_status(self.agent, allowed, "IN_PROGRESS").status_code, 200)
        response = self.patch_status(self.agent, rejected, "OPEN")
        self.assertEqual(response.status_code, 400)
        self.assertIn("status", response.json()["error"]["details"])

    def test_employee_creator_transition_rules(self):
        ticket = self.make_ticket("SD-3004", "Employee issue", self.employee, status="OPEN")
        self.assertEqual(self.patch_status(self.employee, ticket, "CLOSED").status_code, 200)
        ticket.status = "RESOLVED"
        ticket.save(update_fields=["status", "updated_at"])
        self.assertEqual(self.patch_status(self.employee, ticket, "IN_PROGRESS").status_code, 200)
        ticket.status = "OPEN"
        ticket.save(update_fields=["status", "updated_at"])
        response = self.patch_status(self.employee, ticket, "IN_PROGRESS")
        self.assertEqual(response.status_code, 400)

    def test_employee_current_assignee_transition_rules(self):
        ticket = self.make_ticket("SD-3005", "Assigned issue", self.agent, status="OPEN")
        self.make_assignment(ticket, self.employee_profile, "ASSIGNED")
        self.assertEqual(self.patch_status(self.employee, ticket, "IN_PROGRESS").status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(self.patch_status(self.employee, ticket, "RESOLVED").status_code, 200)

    def test_employee_historical_assignment_does_not_grant_status_access(self):
        ticket = self.make_ticket("SD-3006", "Historical issue", self.agent, status="OPEN")
        self.make_assignment(ticket, self.employee_profile, "COMPLETED")
        response = self.patch_status(self.employee, ticket, "IN_PROGRESS")
        self.assertEqual(response.status_code, 404)

    def test_shared_policy_is_used_for_status_decisions(self):
        ticket = self.make_ticket("SD-3007", "Policy issue", self.employee, status="OPEN")
        self.assertTrue(can_transition_ticket_status(self.employee, ticket, "CLOSED"))
        self.assertFalse(can_transition_ticket_status(self.employee, ticket, "IN_PROGRESS"))
        self.assertTrue(can_transition_ticket_status(self.admin, ticket, "CLOSED"))


    def test_bulk_status_validation_is_all_or_nothing(self):
        valid_if_alone = self.make_ticket("SD-4001", "Open", self.admin, status="OPEN")
        invalid = self.make_ticket("SD-4002", "Closed", self.admin, status="CLOSED")
        response = self.client_for(self.agent).post(
            "/api/tickets/bulk/",
            {"ticket_ids": [valid_if_alone.pk, invalid.pk], "action": "set_status", "value": "IN_PROGRESS"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        valid_if_alone.refresh_from_db()
        invalid.refresh_from_db()
        self.assertEqual(valid_if_alone.status, "OPEN")
        self.assertEqual(invalid.status, "CLOSED")

    def test_bulk_updates_status_and_priority(self):
        first = self.make_ticket("SD-4003", "First", self.admin, status="OPEN")
        second = self.make_ticket("SD-4004", "Second", self.admin, status="IN_PROGRESS")
        initial_timestamps = {first.pk: first.updated_at, second.pk: second.updated_at}
        client = self.client_for(self.admin)
        status_response = client.post(
            "/api/tickets/bulk/",
            {"ticket_ids": [first.pk, second.pk], "action": "set_status", "value": "IN_PROGRESS"},
            format="json",
        )
        self.assertEqual(status_response.status_code, 200)
        status_timestamps = {
            row["id"]: parse_datetime(row["updated_at"])
            for row in status_response.json()["data"]
        }
        for ticket_id, initial in initial_timestamps.items():
            self.assertGreater(status_timestamps[ticket_id], initial)
        priority_response = client.post(
            "/api/tickets/bulk/",
            {"ticket_ids": [first.pk, second.pk], "action": "set_priority", "value": "HIGH"},
            format="json",
        )
        self.assertEqual(priority_response.status_code, 200)
        self.assertTrue(all(row["priority"] == "HIGH" for row in priority_response.json()["data"]))
        priority_timestamps = {
            row["id"]: parse_datetime(row["updated_at"])
            for row in priority_response.json()["data"]
        }
        for ticket_id, updated_at in status_timestamps.items():
            self.assertGreater(priority_timestamps[ticket_id], updated_at)

    def test_bulk_rejects_employees_and_duplicate_ids(self):
        denied = self.client_for(self.employee).post(
            "/api/tickets/bulk/",
            {"ticket_ids": [self.created.pk], "action": "set_priority", "value": "HIGH"},
            format="json",
        )
        duplicate = self.client_for(self.admin).post(
            "/api/tickets/bulk/",
            {"ticket_ids": [self.created.pk, self.created.pk], "action": "set_priority", "value": "HIGH"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(duplicate.status_code, 400)

    def test_bulk_database_conflict_rolls_back_prior_updates(self):
        first = self.make_ticket("SD-4005", "First atomic", self.admin)
        second = self.make_ticket("SD-4006", "Second atomic", self.admin)
        from tickets import services

        original = services._conditional_bulk_update
        calls = {"count": 0}

        def fail_after_first(ticket, *, field, value):
            calls["count"] += 1
            if calls["count"] == 2:
                raise Conflict("Simulated concurrent conflict")
            return original(ticket, field=field, value=value)

        with patch("tickets.services._conditional_bulk_update", side_effect=fail_after_first):
            with self.assertRaises(Conflict):
                services.apply_bulk_ticket_update([first, second], field="priority", value="HIGH", actor=self.admin)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.priority, "MEDIUM")
        self.assertEqual(second.priority, "MEDIUM")

    def test_conditional_update_rejects_a_stale_database_snapshot(self):
        ticket = self.make_ticket("SD-4007", "Concurrent", self.admin)
        stale_copy = Ticket.objects.get(pk=ticket.pk)
        Ticket.objects.filter(pk=ticket.pk).update(
            title="Changed elsewhere",
            updated_at=ticket.updated_at + timedelta(seconds=1),
        )
        with self.assertRaises(Conflict):
            update_ticket_if_unchanged(stale_copy, actor=self.admin, title="Stale overwrite")
        ticket.refresh_from_db()
        self.assertEqual(ticket.title, "Changed elsewhere")

    def test_expected_updated_at_rejects_stale_client_update(self):
        ticket = self.make_ticket("SD-4008", "Expected timestamp", self.admin)
        stale_timestamp = ticket.updated_at.isoformat()
        Ticket.objects.filter(pk=ticket.pk).update(
            title="Newer title",
            updated_at=ticket.updated_at + timedelta(seconds=1),
        )
        response = self.client_for(self.admin).patch(
            f"/api/tickets/{ticket.pk}/",
            {"title": "Stale title", "expected_updated_at": stale_timestamp},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        ticket.refresh_from_db()
        self.assertEqual(ticket.title, "Newer title")

    def test_patch_timestamp_client_round_trip(self):
        ticket = self.make_ticket("SD-4010", "Round trip", self.admin)
        client = self.client_for(self.admin)
        detail = client.get(f"/api/tickets/{ticket.pk}/")
        self.assertEqual(detail.status_code, 200)
        expected_updated_at = detail.json()["data"]["updated_at"]

        successful = client.patch(
            f"/api/tickets/{ticket.pk}/",
            {"title": "First update", "expected_updated_at": expected_updated_at},
            format="json",
        )
        self.assertEqual(successful.status_code, 200)
        new_updated_at = successful.json()["data"]["updated_at"]
        self.assertGreater(parse_datetime(new_updated_at), parse_datetime(expected_updated_at))

        replayed = client.patch(
            f"/api/tickets/{ticket.pk}/",
            {"title": "Stale replay", "expected_updated_at": expected_updated_at},
            format="json",
        )
        self.assertEqual(replayed.status_code, 409)
        ticket.refresh_from_db()
        self.assertEqual(ticket.title, "First update")

    def test_patch_requires_valid_expected_updated_at(self):
        ticket = self.make_ticket("SD-4009", "Timestamp required", self.admin)
        client = self.client_for(self.admin)
        missing = client.patch(
            f"/api/tickets/{ticket.pk}/",
            {"title": "Missing timestamp"},
            format="json",
        )
        invalid = client.patch(
            f"/api/tickets/{ticket.pk}/",
            {"title": "Invalid timestamp", "expected_updated_at": "not-a-timestamp"},
            format="json",
        )
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.json()["error"]["code"], "validation_error")
        self.assertIn("expected_updated_at", missing.json()["error"]["details"])
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["error"]["code"], "validation_error")


class TicketArchiveApiTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Archive Support", code="ARCH")
        self.admin = User.objects.create_user("archive-admin", password="test-pass", role="ADMIN")
        self.agent = User.objects.create_user("archive-agent", password="test-pass", role="AGENT")
        self.employee = User.objects.create_user("archive-employee", password="test-pass", role="EMPLOYEE")
        self.profile = EmployeeProfile.objects.create(
            user=self.employee,
            employee_id="ARCH-EMP-1",
            department=self.department,
            designation="Support Engineer",
        )
        self.ticket = Ticket.objects.create(
            ticket_id="SD-ARCHIVE-1",
            title="Archive preservation test",
            description="Ticket and related history must be retained.",
            created_by=self.employee,
            department=self.department,
        )

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def add_related_records(self):
        assignment = Assignment.objects.create(
            ticket=self.ticket,
            assigned_to=self.profile,
            assigned_by=self.agent,
            status="ACCEPTED",
            remarks="Keep this history when archiving.",
        )
        analysis = TicketAnalysis.objects.create(
            ticket=self.ticket,
            predicted_category="Access",
            predicted_priority="High",
            sentiment="Negative",
            confidence_score=0.8,
            suggested_response="We will investigate.",
        )
        return assignment, analysis

    def test_admin_and_agent_can_archive_idempotently_without_deleting_related_data(self):
        assignment, analysis = self.add_related_records()
        response = self.client_for(self.agent).post(f"/api/tickets/{self.ticket.pk}/archive/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        body = response.json()["data"]
        self.assertTrue(body["is_archived"])
        self.assertEqual(body["archived_by"]["id"], self.agent.pk)
        self.assertTrue(body["archived_at"])
        self.assertEqual(body["ticket_id"], "SD-ARCHIVE-1")
        self.assertEqual(body["status"], "OPEN")
        first_archived_at = body["archived_at"]
        first_updated_at = body["updated_at"]

        repeated = self.client_for(self.admin).post(f"/api/tickets/{self.ticket.pk}/archive/", {}, format="json")
        self.assertEqual(repeated.status_code, 200)
        repeated_body = repeated.json()["data"]
        self.assertEqual(repeated_body["archived_at"], first_archived_at)
        self.assertEqual(repeated_body["updated_at"], first_updated_at)
        self.assertEqual(repeated_body["archived_by"]["id"], self.agent.pk)

        self.assertTrue(Ticket.objects.filter(pk=self.ticket.pk, is_archived=True).exists())
        self.assertTrue(Assignment.objects.filter(pk=assignment.pk, status="ACCEPTED").exists())
        self.assertTrue(TicketAnalysis.objects.filter(pk=analysis.pk, ticket=self.ticket).exists())

    def test_employee_cannot_archive_and_archived_ticket_detail_is_admin_only(self):
        denied = self.client_for(self.employee).post(
            f"/api/tickets/{self.ticket.pk}/archive/", {}, format="json"
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["error"]["code"], "permission_denied")

        self.client_for(self.admin).post(f"/api/tickets/{self.ticket.pk}/archive/", {}, format="json")
        self.assertEqual(self.client_for(self.admin).get(f"/api/tickets/{self.ticket.pk}/").status_code, 200)
        for user in (self.agent, self.employee):
            response = self.client_for(user).get(f"/api/tickets/{self.ticket.pk}/")
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_archived_ticket_is_excluded_from_active_results_search_counts_and_bulk(self):
        assignment, _analysis = self.add_related_records()
        self.client_for(self.admin).post(f"/api/tickets/{self.ticket.pk}/archive/", {}, format="json")

        for user in (self.admin, self.agent, self.employee):
            listing = self.client_for(user).get("/api/tickets/?search=SD-ARCHIVE-1")
            self.assertEqual(listing.status_code, 200)
            self.assertEqual(listing.json()["data"], [])
            self.assertEqual(listing.json()["meta"]["pagination"]["count"], 0)

        bulk = self.client_for(self.admin).post(
            "/api/tickets/bulk/",
            {"ticket_ids": [self.ticket.pk], "action": "set_priority", "value": "HIGH"},
            format="json",
        )
        self.assertEqual(bulk.status_code, 404)
        self.assertEqual(bulk.json()["error"]["code"], "not_found")

        # Assignment history remains available to ADMIN but is not exposed as
        # an active assignment listing to AGENT or EMPLOYEE after archiving.
        admin_assignments = self.client_for(self.admin).get("/api/assignments/?ticket=%s" % self.ticket.pk)
        self.assertEqual(admin_assignments.status_code, 200)
        self.assertEqual(admin_assignments.json()["meta"]["pagination"]["count"], 1)
        self.assertEqual(admin_assignments.json()["data"][0]["id"], assignment.pk)
        for user in (self.agent, self.employee):
            rows = self.client_for(user).get("/api/assignments/?ticket=%s" % self.ticket.pk)
            self.assertEqual(rows.status_code, 200)
            self.assertEqual(rows.json()["data"], [])

        analysis = self.client_for(self.employee).post(
            f"/api/ai/analyze/{self.ticket.pk}/", {}, format="json"
        )
        self.assertEqual(analysis.status_code, 404)
        self.assertEqual(analysis.json()["error"]["code"], "not_found")
        self.assertEqual(Assignment.objects.filter(ticket=self.ticket).count(), 1)
        self.assertEqual(TicketAnalysis.objects.filter(ticket=self.ticket).count(), 1)

    def test_only_admin_can_list_archived_tickets_with_common_pagination(self):
        self.client_for(self.admin).post(f"/api/tickets/{self.ticket.pk}/archive/", {}, format="json")
        response = self.client_for(self.admin).get("/api/tickets/archived/?page=1&page_size=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["meta"]["pagination"]["count"], 1)
        self.assertTrue(response.json()["data"][0]["is_archived"])

        for user in (self.agent, self.employee):
            denied = self.client_for(user).get("/api/tickets/archived/")
            self.assertEqual(denied.status_code, 403)
            self.assertEqual(denied.json()["error"]["code"], "permission_denied")

    def test_only_admin_can_restore_and_restore_is_idempotent(self):
        assignment, analysis = self.add_related_records()
        self.client_for(self.agent).post(f"/api/tickets/{self.ticket.pk}/archive/", {}, format="json")
        for user in (self.agent, self.employee):
            denied = self.client_for(user).post(f"/api/tickets/{self.ticket.pk}/restore/", {}, format="json")
            self.assertEqual(denied.status_code, 403)

        client = self.client_for(self.admin)
        restored = client.post(f"/api/tickets/{self.ticket.pk}/restore/", {}, format="json")
        self.assertEqual(restored.status_code, 200)
        body = restored.json()["data"]
        self.assertFalse(body["is_archived"])
        self.assertIsNone(body["archived_at"])
        self.assertIsNone(body["archived_by"])
        updated_at = body["updated_at"]

        repeated = client.post(f"/api/tickets/{self.ticket.pk}/restore/", {}, format="json")
        self.assertEqual(repeated.status_code, 200)
        self.assertFalse(repeated.json()["data"]["is_archived"])
        self.assertEqual(repeated.json()["data"]["updated_at"], updated_at)
        self.assertFalse(Ticket.objects.get(pk=self.ticket.pk).is_archived)
        self.assertTrue(Assignment.objects.filter(pk=assignment.pk).exists())
        self.assertTrue(TicketAnalysis.objects.filter(pk=analysis.pk).exists())
        active = client.get("/api/tickets/?search=SD-ARCHIVE-1")
        self.assertEqual(active.json()["meta"]["pagination"]["count"], 1)

    def test_archive_requires_csrf_for_session_authenticated_writes(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.agent)
        rejected = client.post(f"/api/tickets/{self.ticket.pk}/archive/", {}, format="json")
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(rejected.json()["error"]["code"], "csrf_failed")
        self.assertFalse(Ticket.objects.get(pk=self.ticket.pk).is_archived)

        token = client.get("/api/auth/csrf/").json()["data"]["csrf_token"]
        accepted = client.post(
            f"/api/tickets/{self.ticket.pk}/archive/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(accepted.status_code, 200)

    def test_archive_uses_stale_snapshot_protection(self):
        stale = Ticket.objects.get(pk=self.ticket.pk)
        Ticket.objects.filter(pk=self.ticket.pk).update(
            title="Concurrent edit",
            updated_at=stale.updated_at + timedelta(seconds=1),
        )
        with self.assertRaises(Conflict):
            archive_ticket(stale, actor=self.admin)
        current = Ticket.objects.get(pk=self.ticket.pk)
        self.assertFalse(current.is_archived)
        self.assertEqual(current.title, "Concurrent edit")

    def test_ticket_delete_method_remains_unsupported(self):
        response = self.client_for(self.admin).delete(f"/api/tickets/{self.ticket.pk}/")
        self.assertEqual(response.status_code, 405)
