from django.urls import path

from .employee_views import EmployeeDetailView, EmployeeListView

urlpatterns = [
    path("", EmployeeListView.as_view(), name="employee-list"),
    path("<int:profile_pk>/", EmployeeDetailView.as_view(), name="employee-detail"),
]
