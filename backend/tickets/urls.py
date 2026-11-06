from django.urls import path

from .views import (
    ArchivedTicketListView,
    TicketArchiveView,
    TicketBulkActionView,
    TicketDetailView,
    TicketListCreateView,
    TicketRestoreView,
)


urlpatterns = [
    path("", TicketListCreateView.as_view(), name="ticket-list-create"),
    path("archived/", ArchivedTicketListView.as_view(), name="ticket-archived-list"),
    path("bulk/", TicketBulkActionView.as_view(), name="ticket-bulk-action"),
    path("<int:pk>/archive/", TicketArchiveView.as_view(), name="ticket-archive"),
    path("<int:pk>/restore/", TicketRestoreView.as_view(), name="ticket-restore"),
    path("<int:pk>/", TicketDetailView.as_view(), name="ticket-detail"),
]
