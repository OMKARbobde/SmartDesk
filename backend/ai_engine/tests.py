from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

from accounts.models import EmployeeProfile
from assignment.models import Assignment
from departments.models import Department
from tickets.models import Ticket
from .models import TicketAnalysis


User = get_user_model()
ANALYZE_URL = "/api/ai/analyze/{}/"


class TicketAnalysisApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("ai-admin", password="test-pass", role="ADMIN")
        self.agent = User.objects.create_user("ai-agent", password="test-pass", role="AGENT")
        self.creator = User.objects.create_user("ai-creator", password="test-pass", role="EMPLOYEE")
        self.assignee = User.objects.create_user("ai-assignee", password="test-pass", role="EMPLOYEE")
        self.outsider = User.objects.create_user("ai-outsider", password="test-pass", role="EMPLOYEE")
        self.unknown_role = User.objects.create_user("ai-unknown", password="test-pass", role="OTHER")
        self.department = Department.objects.create(name="AI Support", code="AIS")
        self.other_department = Department.objects.create(name="AI Finance", code="AIF")
        self.assignee_profile = EmployeeProfile.objects.create(
            user=self.assignee,
            employee_id="AI-EMP-1",
            department=self.department,
            designation="Support Agent",
        )
        self.own_ticket = Ticket.objects.create(
            ticket_id="SD-AI-OWN",
            title="Laptop login problem, frustrated",
            description="The computer login is blocked and I am frustrated.",
            created_by=self.creator,
            department=self.department,
        )
        self.other_ticket = Ticket.objects.create(
            ticket_id="SD-AI-OTHER",
            title="Payment issue",
            description="Need help with an invoice.",
            created_by=self.outsider,
            department=self.other_department,
        )
        self.client = APIClient()

    def url(self, ticket=None):
        return ANALYZE_URL.format(ticket or self.own_ticket.pk)

    def test_admin_and_agent_can_analyze_across_departments(self):
        for user in (self.admin, self.agent):
            with self.subTest(role=user.role):
                self.client.force_authenticate(user)
                response = self.client.post(self.url(self.other_ticket.pk), {}, format="json")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["data"]["ticket_id"], self.other_ticket.ticket_id)
                self.assertEqual(response.json()["meta"], {})

    def test_employee_can_analyze_ticket_they_created(self):
        self.client.force_authenticate(self.creator)
        response = self.client.post(self.url(), {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["ticket_id"], self.own_ticket.ticket_id)

    def test_employee_can_analyze_current_assigned_and_accepted_tickets(self):
        for index, assignment_status in enumerate(("ASSIGNED", "ACCEPTED")):
            ticket = Ticket.objects.create(
                ticket_id=f"SD-AI-AS{index}",
                title="Network problem",
                description="The network is not working.",
                created_by=self.outsider,
                department=self.other_department,
            )
            Assignment.objects.create(
                ticket=ticket,
                assigned_to=self.assignee_profile,
                status=assignment_status,
            )
            with self.subTest(assignment_status=assignment_status):
                self.client.force_authenticate(self.assignee)
                response = self.client.post(self.url(ticket.pk), {}, format="json")
                self.assertEqual(response.status_code, 200)

    def test_employee_cannot_analyze_unrelated_ticket_and_service_is_not_called(self):
        self.client.force_authenticate(self.creator)
        with patch("ai_engine.views.analyze_ticket") as analyze:
            response = self.client.post(self.url(self.other_ticket.pk), {}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")
        self.assertEqual(response.json()["error"]["details"], {})
        analyze.assert_not_called()
        self.assertFalse(TicketAnalysis.objects.filter(ticket=self.other_ticket).exists())

    def test_historical_assignment_does_not_grant_employee_visibility(self):
        Assignment.objects.create(
            ticket=self.other_ticket,
            assigned_to=self.assignee_profile,
            status="REASSIGNED",
        )
        self.client.force_authenticate(self.assignee)
        response = self.client.post(self.url(self.other_ticket.pk), {}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")
        self.assertFalse(TicketAnalysis.objects.filter(ticket=self.other_ticket).exists())

    def test_success_envelope_canonical_enums_and_persisted_timestamp(self):
        self.client.force_authenticate(self.creator)
        response = self.client.post(self.url(), {}, format="json")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), {"data", "meta"})
        self.assertEqual(body["meta"], {})
        data = body["data"]
        self.assertEqual(data["message"], "Ticket analyzed successfully")
        self.assertEqual(data["ticket_id"], self.own_ticket.ticket_id)
        self.assertEqual(data["predicted_priority"], "HIGH")
        self.assertEqual(data["sentiment"], "NEGATIVE")
        self.assertIsInstance(data["predicted_category"], str)
        self.assertIsInstance(data["confidence_score"], float)
        self.assertIsInstance(data["suggested_response"], str)
        self.assertTrue(data["analyzed_at"].endswith("Z"))
        saved = TicketAnalysis.objects.get(ticket=self.own_ticket)
        self.assertEqual(parse_datetime(data["analyzed_at"]), saved.analyzed_at)

    def test_reanalysis_updates_existing_record_and_returns_latest_saved_values(self):
        self.client.force_authenticate(self.creator)
        first = self.client.post(self.url(), {}, format="json")
        first_analysis = TicketAnalysis.objects.get(ticket=self.own_ticket)
        first_id = first_analysis.pk
        self.own_ticket.title = "URGENT critical server down"
        self.own_ticket.description = "Security breach; the server is down."
        self.own_ticket.save(update_fields=("title", "description"))
        second = self.client.post(self.url(), {}, format="json")
        second_analysis = TicketAnalysis.objects.get(ticket=self.own_ticket)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second_analysis.pk, first_id)
        self.assertEqual(TicketAnalysis.objects.filter(ticket=self.own_ticket).count(), 1)
        self.assertEqual(second.json()["data"]["predicted_priority"], "CRITICAL")
        self.assertEqual(parse_datetime(second.json()["data"]["analyzed_at"]), second_analysis.analyzed_at)

    def test_omitted_request_body_is_accepted_as_empty_object(self):
        self.client.force_authenticate(self.creator)
        response = self.client.post(self.url())
        self.assertEqual(response.status_code, 200)

    def test_nonempty_null_and_list_payloads_are_validation_errors(self):
        self.client.force_authenticate(self.creator)
        payloads = (
            ({"unexpected": "value"}, "json"),
            ("null", "application/json"),
            ('["value"]', "application/json"),
        )
        for payload, content_type in payloads:
            with self.subTest(payload=payload):
                if content_type == "json":
                    response = self.client.post(self.url(), payload, format="json")
                else:
                    response = self.client.generic("POST", self.url(), data=payload, content_type=content_type)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_malformed_json_uses_validation_error_envelope(self):
        self.client.force_authenticate(self.creator)
        response = self.client.generic(
            "POST", self.url(), data="{", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_missing_ticket_returns_standard_not_found_and_does_not_analyze(self):
        self.client.force_authenticate(self.admin)
        with patch("ai_engine.views.analyze_ticket") as analyze:
            response = self.client.post(self.url(999999), {}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")
        analyze.assert_not_called()

    def test_unauthenticated_request_returns_json_401_not_redirect(self):
        response = self.client.post(self.url(), {}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "not_authenticated")
        self.assertNotIn("Location", response)

    def test_unsupported_role_is_forbidden(self):
        self.client.force_authenticate(self.unknown_role)
        response = self.client.post(self.url(), {}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "permission_denied")

    def test_authenticated_post_requires_csrf_and_returns_standard_error(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.creator)
        response = client.post(self.url(), {}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "csrf_failed")
        self.assertEqual(response.json()["error"]["details"], {})

    def test_csrf_bootstrap_token_allows_authenticated_post(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.creator)
        bootstrap = client.get("/api/auth/csrf/")
        token = bootstrap.json()["data"]["csrf_token"]
        response = client.post(self.url(), {}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)

    def test_non_post_method_uses_standard_method_not_allowed_envelope(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()["error"]["code"], "method_not_allowed")
