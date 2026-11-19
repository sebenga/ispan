from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.spa import spa_index
from apps.core.views import health_check

api_v1 = [
    path("auth/", include("apps.accounts.urls")),
    path("legal/", include("apps.legal.urls")),
    path("", include("apps.workers.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.jobs.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", health_check, name="health"),
    path("api/healthz/", health_check, name="api-health"),
    path("api/v1/", include(api_v1)),
    path("api/legal/", include("apps.legal.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("", spa_index, name="spa"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "apps.core.spa.not_found"
