from django.urls import path
from . import views

urlpatterns = [
    path("trip/plan/", views.plan_trip_view, name="trip-plan"),
    path("health/",    views.health_check,   name="health-check"),
]
