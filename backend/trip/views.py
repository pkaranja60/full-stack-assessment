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
from logs.log_generator import generate_trip_logs
import zipfile
import io
from django.http import HttpResponse, FileResponse

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
        stop_loc_clean = stop_loc.strip().lower()
        
        # 1. Try fuzzy match first (matches "Fuel stop near Chicago" to "Chicago")
        coords = None
        for known_loc, known_coords in location_coords.items():
            known_loc_clean = known_loc.strip().lower()
            if known_loc_clean in stop_loc_clean or stop_loc_clean in known_loc_clean:
                coords = known_coords
                break
        
        # 2. If still no coordinates, geocode this new location on the fly
        if not coords and stop_loc:
            try:
                from .services.route_service import geocode
                import time
                time.sleep(1.0) # Respect rate limits
                geo = geocode(stop_loc)
                coords = {"lat": geo["lat"], "lon": geo["lon"]}
                location_coords[stop_loc] = coords # Cache it for the rest of this loop
            except Exception:
                logger.warning("Failed to geocode intermediate stop: %s", stop_loc)
        
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
        recap = log_data.get("recap", {})
        daily_log = DailyLog.objects.create(
            trip                      = trip,
            day                       = log_data["day"],
            label                     = log_data["label"],
            total_off_duty            = totals.get("off_duty", 0.0),
            total_sleeper_berth       = totals.get("sleeper_berth", 0.0),
            total_driving             = totals.get("driving", 0.0),
            total_on_duty_not_driving = totals.get("on_duty_not_driving", 0.0),
            cycle_hours_after         = recap.get("cycle_hours_after"),
            cycle_hours_remaining     = recap.get("cycle_hours_remaining"),
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
        stop_loc_clean = stop_loc.strip().lower()
        
        # 1. Try fuzzy match first
        coords = None
        for known_loc, known_coords in location_coords.items():
            known_loc_clean = known_loc.strip().lower()
            if known_loc_clean in stop_loc_clean or stop_loc_clean in known_loc_clean:
                coords = known_coords
                break
        
        # 2. If still no coordinates, geocode it
        if not coords and stop_loc:
            try:
                from .services.route_service import geocode
                import time
                time.sleep(1.0)
                geo = geocode(stop_loc)
                coords = {"lat": geo["lat"], "lon": geo["lon"]}
                location_coords[stop_loc] = coords
            except Exception:
                pass
        
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
def download_trip_logs_view(request: Request, trip_id: str) -> HttpResponse:
    """
    GET /api/trip/<trip_id>/download-logs/
    Generates PNG log sheets for every day and returns them in a ZIP archive.
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

    # 1. Prepare trip data for the generator (matching serializer format)
    trip_data = TripSerializer(trip).data

    # 2. Generate log images
    try:
        log_results = generate_trip_logs(trip_data)
    except Exception as exc:
        logger.exception("Failed to generate log images")
        return Response(
            {"success": False, "error": f"Log generation failed: {exc}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # 3. Create ZIP archive in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for res in log_results:
            day_num = res["day"]
            img_bytes = res["image_bytes"]
            zip_file.writestr(f"Daily_Log_Day_{day_num}.png", img_bytes)

    zip_buffer.seek(0)

    # 4. Return as attachment
    filename = f"Trip_Logs_{trip.current_location[:20]}_to_{trip.dropoff_location[:20]}.zip"
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["GET"])
def health_check(request: Request) -> Response:
    return Response({"status": "ok", "service": "ELD Trip Planner API"})