"""
URL configuration for smartdesk project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from assignment.views import TicketAssignmentCreateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication and current-user API
    path('api/', include('accounts.urls')),

    # Ticket API
    path('api/tickets/', include('tickets.urls')),

    # Department, employee, and assignment APIs
    path('api/departments/', include('departments.urls')),
    path('api/analytics/', include('departments.analytics_urls')),
    path('api/employees/', include('accounts.employee_urls')),
    path('api/assignments/', include('assignment.urls')),
    path('api/tickets/<int:ticket_id>/assignments/', TicketAssignmentCreateView.as_view(), name='ticket-assignment-create'),
    # Persistent, ADMIN-only audit trail
    path('api/audit-logs/', include('auditlog.urls')),

    # AI Engine API
    path('api/ai/', include('ai_engine.urls')),
]
