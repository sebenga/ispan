from django.urls import path

from .views import JobAcceptView, JobDetailView, JobListCreateView, JobRateView, JobStatusView

urlpatterns = [
    path("jobs/", JobListCreateView.as_view(), name="jobs"),
    path("jobs/<uuid:job_id>/", JobDetailView.as_view(), name="job-detail"),
    path("jobs/<uuid:job_id>/accept/", JobAcceptView.as_view(), name="job-accept"),
    path("jobs/<uuid:job_id>/status/", JobStatusView.as_view(), name="job-status"),
    path("jobs/<uuid:job_id>/rate/", JobRateView.as_view(), name="job-rate"),
]
