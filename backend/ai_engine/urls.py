
from django.urls import path
from . import views

urlpatterns = [
    path(
        'analyze/<int:ticket_id>/',
        views.analyze_ticket_view,
        name='analyze_ticket'
    ),
]
