from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MockNotification


class MockInboxView(APIView):
    """Dev-only mock SMS/email inbox. Never expose OTP bodies in production UIs without auth."""

    def get(self, request):
        qs = MockNotification.objects.all()[:50]
        if request.user.is_authenticated and not (request.user.is_staff or request.user.is_support):
            qs = MockNotification.objects.filter(user=request.user)[:50]
        return Response(
            [
                {
                    "id": str(n.id),
                    "channel": n.channel,
                    "destination": n.destination,
                    "template": n.template,
                    "subject": n.subject,
                    "body": n.body,
                    "created_at": n.created_at,
                }
                for n in qs
            ]
        )
