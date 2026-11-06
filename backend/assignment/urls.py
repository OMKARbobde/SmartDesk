from django.urls import path

from .views import AssignmentDetailView, AssignmentListView, TicketAssignmentCreateView

urlpatterns = [
    path("", AssignmentListView.as_view(), name="assignment-list"),
    path("<int:pk>/", AssignmentDetailView.as_view(), name="assignment-detail"),
]

ticket_assignment_urlpatterns = [
    path("<int:ticket_id>/assignments/", TicketAssignmentCreateView.as_view(), name="ticket-assignment-create"),
]
