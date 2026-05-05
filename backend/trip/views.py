import logging

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from .serializers import (
    TripPlanRequestSerializer,
    TripSerializer,
    TripListSerializer,
)
from .services.hos_calculator import plan_trip
from .services.route_service import get_route_info
from .models import Trip, TripStop, TripSegment, DailyLog, DailyLogSegment

logger = logging.getLogger(__name__)


def _save_trip(data, route_info, trip_plan) -> Trip:
    """Persist the full trip plan to the database and return the Trip instance."""

    # ── Trip (top-level) ──────────────────────────────────────────────────────
    summary = trip_plan["summary"]
    s       = summary

    trip = Trip.objects.create(
        current_location     = data["current_location"],
        pickup_location      = data["pickup_location"],
        dropoff_location     = data["dropoff_location"],
        current_cycle_used   = data["current_cycle_used"],
        total_distance_miles = route_info["total_distance_miles"],
        total_duration_hours = route_info["total_duration_hours"],
        route_geometry       = route_info["geometry"],
        current_lat          = route_info["current_coords"]["lat"],
        current_lon          = route_info["current_coords"]["lon"],
        pickup_lat           = route_info["pickup_coords"]["lat"],
        pickup_lon           = route_info["pickup_coords"]["lon"],
        dropoff_lat          = route_info["dropoff_coords"]["lat"],
        dropoff_lon          = route_info["dropoff_coords"]["lon"],
        total_driving_hours  = s["total_driving_hours"],
        trip_duration_hours  = s["trip_duration_hours"],
        total_days           = s["total_days"],
        cycle_hours_after    = s["cycle_hours_after"],
        num_rest_stops       = s["num_rest_stops"],
        num_fuel_stops       = s["num_fuel_stops"],
        num_breaks           = s["num_breaks"],
    )

    # ── Stops ──────────────────────────────────────────────────────────────────
    location_coords = {
        data["current_location"]: route_info["current_coords"],
        data["pickup_location"]:  route_info["pickup_coords"],
        data["dropoff_location"]: route_info["dropoff_coords"],
    }

    stop_objs = []
    for order, stop in enumerate(trip_plan["stops"]):
        stop_loc = stop.get("location", "")
        
        # Fuzzy match for coordinates
        coords = location_coords.get(stop_loc)
        if not coords:
            for known_loc, known_coords in location_coords.items():
                if known_loc in stop_loc:
                    coords = known_coords
                    break
        
        stop_objs.append(TripStop(
            trip           = trip,
            stop_type      = stop["stop_type"],
            location       = stop_loc,
            lat            = coords.get("lat") if coords else None,
            lon            = coords.get("lon") if coords else None,
            hour_absolute  = stop["hour_absolute"],
            time_label     = stop["time_label"],
            duration_hours = stop.get("duration_hours", 0.0),
            description    = stop.get("description", ""),
            order          = order,
        ))
    TripStop.objects.bulk_create(stop_objs)

    # ── Flat segments ─────────────────────────────────────────────────────────
    seg_objs = []
    for seg in trip_plan["segments"]:
        seg_objs.append(TripSegment(
            trip        = trip,
            status      = seg["status"],
            start       = seg["start"],
            end         = seg["end"],
            duration    = seg["duration"],
            description = seg.get("description", ""),
            location    = seg.get("location", ""),
            miles       = seg.get("miles", 0.0),
            day         = seg.get("day", 1),
            start_time  = seg.get("start_time", ""),
            end_time    = seg.get("end_time", ""),
        ))
    TripSegment.objects.bulk_create(seg_objs)

    # ── Daily logs + per-day segments ─────────────────────────────────────────
    for log_data in trip_plan["daily_logs"]:
        totals = log_data["totals"]
        daily_log = DailyLog.objects.create(
            trip                      = trip,
            day                       = log_data["day"],
            label                     = log_data["label"],
            total_off_duty            = totals.get("off_duty", 0.0),
            total_sleeper_berth       = totals.get("sleeper_berth", 0.0),
            total_driving             = totals.get("driving", 0.0),
            total_on_duty_not_driving = totals.get("on_duty_not_driving", 0.0),
        )

        log_seg_objs = []
        for seg in log_data["segments"]:
            log_seg_objs.append(DailyLogSegment(
                daily_log   = daily_log,
                status      = seg["status"],
                start_hour  = seg["start_hour"],
                end_hour    = seg["end_hour"],
                duration    = seg["duration"],
                description = seg.get("description", ""),
                location    = seg.get("location", ""),
                start_time  = seg.get("start_time", ""),
                end_time    = seg.get("end_time", ""),
            ))
        DailyLogSegment.objects.bulk_create(log_seg_objs)

    return trip


@api_view(["POST"])
def plan_trip_view(request: Request) -> Response:
    """
    POST /api/trip/plan/

    Body:
        current_location   : str
        pickup_location    : str
        dropoff_location   : str
        current_cycle_used : float (0–69.9)
    """
    serializer = TripPlanRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data

    # 1. Geocode + routing
    try:
        route_info = get_route_info(
            data["current_location"],
            data["pickup_location"],
            data["dropoff_location"],
        )
    except ValueError as exc:
        logger.warning("Route lookup failed: %s", exc)
        return Response(
            {"success": False, "error": str(exc)},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    legs       = route_info["legs"]
    leg1_miles = legs[0]["distance_miles"] if len(legs) > 0 else 0.0
    leg2_miles = legs[1]["distance_miles"] if len(legs) > 1 else 0.0

    if leg1_miles + leg2_miles < 0.5:
        return Response(
            {"success": False, "error": "Route distance is too short to plan."},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # 2. HOS planning
    try:
        trip_plan = plan_trip(
            leg1_miles        = leg1_miles,
            leg2_miles        = leg2_miles,
            cycle_hours_used  = data["current_cycle_used"],
            current_location  = data["current_location"],
            pickup_location   = data["pickup_location"],
            dropoff_location  = data["dropoff_location"],
        )
    except Exception as exc:
        logger.exception("HOS planning error")
        return Response(
            {"success": False, "error": f"Trip planning error: {exc}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # 3. Persist to DB
    try:
        trip = _save_trip(data, route_info, trip_plan)
    except Exception as exc:
        logger.exception("DB save error")
        return Response(
            {"success": False, "error": f"Failed to save trip: {exc}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # 4. Enrich stops with coordinates for response
    location_coords = {
        data["current_location"]: route_info["current_coords"],
        data["pickup_location"]:  route_info["pickup_coords"],
        data["dropoff_location"]: route_info["dropoff_coords"],
    }
    enriched_stops = []
    for stop in trip_plan["stops"]:
        stop_copy = dict(stop)
        stop_loc = stop.get("location", "")
        
        # Try exact match first, then fuzzy match for "near X" locations
        coords = location_coords.get(stop_loc)
        if not coords:
            for known_loc, known_coords in location_coords.items():
                if known_loc in stop_loc:
                    coords = known_coords
                    break
        
        if coords:
            stop_copy["coordinates"] = [coords["lon"], coords["lat"]]
        enriched_stops.append(stop_copy)

    enriched_legs = []
    if len(legs) >= 1:
        enriched_legs.append({**legs[0], "from": data["current_location"], "to": data["pickup_location"]})
    if len(legs) >= 2:
        enriched_legs.append({**legs[1], "from": data["pickup_location"], "to": data["dropoff_location"]})

    return Response({
        "success":    True,
        "trip_id":    str(trip.id),
        "route": {
            "geometry":             route_info["geometry"],
            "total_distance_miles": route_info["total_distance_miles"],
            "total_duration_hours": route_info["total_duration_hours"],
            "waypoints":            route_info["waypoints"],
            "legs":                 enriched_legs,
        },
        "daily_logs": trip_plan["daily_logs"],
        "stops":      enriched_stops,
        "summary":    trip_plan["summary"],
        "segments":   trip_plan["segments"],
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def get_trip_view(request: Request, trip_id: str) -> Response:
    """
    GET /api/trip/<trip_id>/
    Retrieve a previously planned trip from the database.
    """
    try:
        trip = Trip.objects.prefetch_related(
            "stops", "segments", "daily_logs__segments"
        ).get(id=trip_id)
    except Trip.DoesNotExist:
        return Response(
            {"success": False, "error": "Trip not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response({
        "success": True,
        **TripSerializer(trip).data,
    })


@api_view(["GET"])
def list_trips_view(request: Request) -> Response:
    """
    GET /api/trips/
    List all planned trips (most recent first).
    """
    trips = Trip.objects.all()[:20]
    return Response({
        "success": True,
        "trips":   TripListSerializer(trips, many=True).data,
    })


@api_view(["GET"])
def health_check(request: Request) -> Response:
    return Response({"status": "ok", "service": "ELD Trip Planner API"})