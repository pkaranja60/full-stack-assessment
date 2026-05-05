from django.urls import path
from . import views

urlpatterns = [
    path("trip/plan/",        views.plan_trip_view,  name="trip-plan"),
    path("trip/<str:trip_id>/", views.get_trip_view, name="trip-detail"),
    path("trip/<str:trip_id>/download-logs/", views.download_trip_logs_view, name="trip-download-logs"),
    path("trips/",            views.list_trips_view, name="trip-list"),
    path("health/",           views.health_check,    name="health-check"),
]