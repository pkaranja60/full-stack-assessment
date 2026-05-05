"""
Route Service — Geocoding + Routing.

Geocoding : geopy Nominatim (OpenStreetMap)
Routing   : OSRM public demo server (free, no key needed)
"""

import time
import logging
import requests
from django.conf import settings
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

logger = logging.getLogger(__name__)

OSRM_URL        = "http://router.project-osrm.org/route/v1/driving"
METERS_PER_MILE = 1609.344
NOMINATIM_DELAY = 1.0   # Nominatim ToS: max 1 request/second


def _get_geocoder() -> Nominatim:
    user_agent = getattr(settings, "NOMINATIM_USER_AGENT", "ELD-Trip-Planner/1.0")
    return Nominatim(user_agent=user_agent)


def geocode(address: str) -> dict:
    """
    Convert a human-readable address to lat/lon using geopy Nominatim.

    Returns:
        {"lat": float, "lon": float, "display_name": str}

    Raises:
        ValueError if the address cannot be geocoded.
    """
    geocoder = _get_geocoder()
    try:
        location = geocoder.geocode(address, exactly_one=True, timeout=10)
    except GeocoderTimedOut:
        raise ValueError(f"Geocoding timed out for address: '{address}'")
    except GeocoderServiceError as exc:
        raise ValueError(f"Geocoding service error for '{address}': {exc}")

    if location is None:
        raise ValueError(f"Could not geocode address: '{address}'")

    return {
        "lat":          location.latitude,
        "lon":          location.longitude,
        "display_name": location.address,
    }


def get_route(
    current_coords: dict,   # {"lat": ..., "lon": ...}
    pickup_coords:  dict,
    dropoff_coords: dict,
) -> dict:
    """
    Fetch a driving route through three waypoints using OSRM.

    Returns:
        geometry, total_distance_miles, total_duration_hours, legs, waypoints
    """
    coords_str = ";".join(
        f"{c['lon']},{c['lat']}"
        for c in [current_coords, pickup_coords, dropoff_coords]
    )
    url    = f"{OSRM_URL}/{coords_str}"
    params = {
        "overview":    "full",
        "geometries":  "geojson",
        "steps":       "false",
        "annotations": "false",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise ValueError(f"Routing request failed: {exc}") from exc

    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError(f"OSRM returned no route: {data.get('message', 'unknown error')}")

    route = data["routes"][0]

    legs = [
        {
            "distance_miles":  round(leg["distance"] / METERS_PER_MILE, 2),
            "duration_hours":  round(leg["duration"] / 3600, 4),
        }
        for leg in route.get("legs", [])
    ]

    waypoints = [
        {
            "name":        wp.get("name", ""),
            "coordinates": [wp["location"][0], wp["location"][1]],  # [lon, lat]
        }
        for wp in data.get("waypoints", [])
    ]

    return {
        "geometry":             route["geometry"],
        "total_distance_miles": round(route["distance"] / METERS_PER_MILE, 2),
        "total_duration_hours": round(route["duration"] / 3600, 4),
        "legs":                 legs,
        "waypoints":            waypoints,
    }


def get_route_info(
    current_location: str,
    pickup_location:  str,
    dropoff_location: str,
) -> dict:
    """
    Full pipeline: geocode three locations via geopy, then fetch the OSRM route.

    Returns merged dict:
        current_coords, pickup_coords, dropoff_coords,
        geometry, total_distance_miles, total_duration_hours, legs, waypoints
    """
    # Geocode — respect Nominatim 1 req/sec limit
    current_geo = geocode(current_location)
    time.sleep(NOMINATIM_DELAY)
    pickup_geo  = geocode(pickup_location)
    time.sleep(NOMINATIM_DELAY)
    dropoff_geo = geocode(dropoff_location)

    # Fetch route
    route = get_route(current_geo, pickup_geo, dropoff_geo)

    # Enrich waypoints with user-supplied names
    location_names = [current_location, pickup_location, dropoff_location]
    geo_results    = [current_geo, pickup_geo, dropoff_geo]

    enriched_waypoints = []
    for i, (name, geo) in enumerate(zip(location_names, geo_results)):
        wp = route["waypoints"][i] if i < len(route["waypoints"]) else {}
        enriched_waypoints.append({
            "name":         name,
            "display_name": geo["display_name"],
            "coordinates":  [geo["lon"], geo["lat"]],
            "snapped_name": wp.get("name", ""),
        })

    return {
        "current_coords":       {"lat": current_geo["lat"], "lon": current_geo["lon"]},
        "pickup_coords":        {"lat": pickup_geo["lat"],  "lon": pickup_geo["lon"]},
        "dropoff_coords":       {"lat": dropoff_geo["lat"], "lon": dropoff_geo["lon"]},
        "geometry":             route["geometry"],
        "total_distance_miles": route["total_distance_miles"],
        "total_duration_hours": route["total_duration_hours"],
        "legs":                 route["legs"],
        "waypoints":            enriched_waypoints,
    }