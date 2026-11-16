from math import ceil

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from accounts.permissions import IsSmartDeskUser
from smartdesk.api import success_response
from .models import Notification
from .serializers import NotificationReadSerializer


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _positive_int(query, field, default):
    values = query.getlist(field)
    if len(values) > 1:
        raise ValidationError({field: ["Provide this parameter once."]})
    raw = values[0] if values else str(default)
    if not raw.isdigit() or int(raw) < 1:
        raise ValidationError({field: ["Use a positive integer."]})
    return int(raw)


class NotificationListView(APIView):
    permission_classes = [IsSmartDeskUser]

    def get(self, request):
        unknown = set(request.query_params.keys()) - {"page", "page_size"}
        if unknown:
            raise ValidationError({key: ["Unsupported query parameter."] for key in sorted(unknown)})
        page = _positive_int(request.query_params, "page", 1)
        page_size = _positive_int(request.query_params, "page_size", DEFAULT_PAGE_SIZE)
        if page_size > MAX_PAGE_SIZE:
            raise ValidationError({"page_size": [f"Use a value from 1 to {MAX_PAGE_SIZE}."]})

        queryset = Notification.objects.filter(recipient=request.user).select_related(
            "related_ticket", "related_assignment"
        ).order_by("-created_at", "-id")
        count = queryset.count()
        total_pages = ceil(count / page_size) if count else 0
        rows = queryset[(page - 1) * page_size:page * page_size] if page <= total_pages else []
        return success_response(NotificationReadSerializer(rows, many=True).data, meta={"pagination": {
            "count": count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "next": page + 1 if page < total_pages else None,
            "previous": page - 1 if 1 < page <= total_pages else None,
        }})


class NotificationUnreadCountView(APIView):
    permission_classes = [IsSmartDeskUser]

    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return success_response({"count": count})


class NotificationMarkReadView(APIView):
    permission_classes = [IsSmartDeskUser]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        if not notification.is_read:
            Notification.objects.filter(pk=notification.pk, recipient=request.user, is_read=False).update(is_read=True)
            notification.refresh_from_db()
        return success_response(NotificationReadSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsSmartDeskUser]

    def post(self, request):
        updated_count = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return success_response({"updated_count": updated_count})
