from django.urls import path

from .realtime_views import (
    JobChatView,
    JobEventsView,
    JobLocationView,
    JobNavigationView,
    JobSosView,
)
from .views import (
    JobAcceptView,
    JobCancelView,
    JobDetailView,
    JobListCreateView,
    JobMatchTickView,
    JobRateView,
    JobStatusView,
    MyOffersView,
    OfferAcceptView,
    OfferDeclineView,
    QuoteAcceptView,
    QuoteListCreateView,
)

urlpatterns = [
    path("jobs/", JobListCreateView.as_view(), name="jobs"),
    path("jobs/offers/mine/", MyOffersView.as_view(), name="my-offers"),
    path("jobs/<uuid:job_id>/", JobDetailView.as_view(), name="job-detail"),
    path("jobs/<uuid:job_id>/cancel/", JobCancelView.as_view(), name="job-cancel"),
    path("jobs/<uuid:job_id>/accept/", JobAcceptView.as_view(), name="job-accept"),
    path("jobs/<uuid:job_id>/status/", JobStatusView.as_view(), name="job-status"),
    path("jobs/<uuid:job_id>/rate/", JobRateView.as_view(), name="job-rate"),
    path("jobs/<uuid:job_id>/match/tick/", JobMatchTickView.as_view(), name="job-match-tick"),
    path("jobs/<uuid:job_id>/quotes/", QuoteListCreateView.as_view(), name="job-quotes"),
    path("jobs/<uuid:job_id>/chat/", JobChatView.as_view(), name="job-chat"),
    path("jobs/<uuid:job_id>/location/", JobLocationView.as_view(), name="job-location"),
    path("jobs/<uuid:job_id>/navigation/", JobNavigationView.as_view(), name="job-navigation"),
    path("jobs/<uuid:job_id>/sos/", JobSosView.as_view(), name="job-sos"),
    path("jobs/<uuid:job_id>/events/", JobEventsView.as_view(), name="job-events"),
    path(
        "jobs/<uuid:job_id>/quotes/<uuid:quote_id>/accept/",
        QuoteAcceptView.as_view(),
        name="job-quote-accept",
    ),
    path(
        "jobs/<uuid:job_id>/offers/<uuid:offer_id>/accept/",
        OfferAcceptView.as_view(),
        name="job-offer-accept",
    ),
    path(
        "jobs/<uuid:job_id>/offers/<uuid:offer_id>/decline/",
        OfferDeclineView.as_view(),
        name="job-offer-decline",
    ),
]
