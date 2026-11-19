from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EmergencyContact


class EmergencyContactView(APIView):
    def get(self, request):
        rows = [
            {
                "id": str(c.id),
                "name": c.name,
                "phone": c.phone,
                "relationship": c.relationship,
                "is_primary": c.is_primary,
            }
            for c in EmergencyContact.objects.filter(user=request.user)
        ]
        return Response({"results": rows})

    def post(self, request):
        name = request.data.get("name")
        phone = request.data.get("phone")
        if not name or not phone:
            return Response({"detail": "name and phone required."}, status=400)
        c = EmergencyContact.objects.create(
            user=request.user,
            name=name,
            phone=phone,
            relationship=request.data.get("relationship", ""),
            is_primary=bool(request.data.get("is_primary", False)),
        )
        return Response({"id": str(c.id)}, status=201)
