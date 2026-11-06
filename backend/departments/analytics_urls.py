from django.urls import path

from .analytics_views import DepartmentAnalyticsView

urlpatterns = [
    path("departments/", DepartmentAnalyticsView.as_view(), name="department-analytics"),
]
