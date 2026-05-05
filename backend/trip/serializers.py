from rest_framework import serializers
from .models import Trip, TripStop, TripSegment, DailyLog, DailyLogSegment


# ── Request ───────────────────────────────────────────────────────────────────

class TripPlanRequestSerializer(serializers.Serializer):
    current_location   = serializers.CharField(max_length=300)
    pickup_location    = serializers.CharField(max_length=300)
    dropoff_location   = serializers.CharField(max_length=300)
    current_cycle_used = serializers.FloatField(min_value=0.0, max_value=70.0)

    def validate_current_cycle_used(self, value):
        if value >= 70.0:
            raise serializers.ValidationError(
                "Cycle hours used cannot be 70 or more — driver is at the legal limit."
            )
        return value


# ── Model serializers ─────────────────────────────────────────────────────────

class TripStopSerializer(serializers.ModelSerializer):
    coordinates = serializers.SerializerMethodField()

    class Meta:
        model  = TripStop
        fields = [
            "stop_type", "location", "coordinates",
            "hour_absolute", "time_label", "duration_hours",
            "description", "order",
        ]

    def get_coordinates(self, obj):
        if obj.lon is not None and obj.lat is not None:
            return [obj.lon, obj.lat]
        return None


class TripSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = TripSegment
        fields = [
            "status", "start", "end", "duration",
            "description", "location", "miles",
            "day", "start_time", "end_time",
        ]


class DailyLogSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DailyLogSegment
        fields = [
            "status", "start_hour", "end_hour", "duration",
            "description", "location", "start_time", "end_time",
        ]


class DailyLogSerializer(serializers.ModelSerializer):
    segments = DailyLogSegmentSerializer(many=True, read_only=True)
    totals   = serializers.SerializerMethodField()
    recap    = serializers.SerializerMethodField()

    class Meta:
        model  = DailyLog
        fields = ["day", "label", "segments", "totals", "recap"]

    def get_recap(self, obj):
        return {
            "cycle_hours_after": obj.cycle_hours_after,
            "cycle_hours_remaining": obj.cycle_hours_remaining,
        }

    def get_totals(self, obj):
        return {
            "off_duty":            obj.total_off_duty,
            "sleeper_berth":       obj.total_sleeper_berth,
            "driving":             obj.total_driving,
            "on_duty_not_driving": obj.total_on_duty_not_driving,
        }


class TripSerializer(serializers.ModelSerializer):
    """Full trip detail — used by GET /api/trip/<id>/"""

    stops      = TripStopSerializer(many=True, read_only=True)
    segments   = TripSegmentSerializer(many=True, read_only=True)
    daily_logs = DailyLogSerializer(many=True, read_only=True)
    route      = serializers.SerializerMethodField()
    summary    = serializers.SerializerMethodField()
    inputs     = serializers.SerializerMethodField()

    class Meta:
        model  = Trip
        fields = [
            "id", "created_at",
            "inputs", "route", "summary",
            "daily_logs", "stops", "segments",
        ]

    def get_inputs(self, obj):
        return {
            "current_location":   obj.current_location,
            "pickup_location":    obj.pickup_location,
            "dropoff_location":   obj.dropoff_location,
            "current_cycle_used": obj.current_cycle_used,
        }

    def get_route(self, obj):
        return {
            "geometry":             obj.route_geometry,
            "total_distance_miles": obj.total_distance_miles,
            "total_duration_hours": obj.total_duration_hours,
            "waypoints": [
                {"name": obj.current_location, "coordinates": [obj.current_lon, obj.current_lat]},
                {"name": obj.pickup_location,  "coordinates": [obj.pickup_lon,  obj.pickup_lat]},
                {"name": obj.dropoff_location, "coordinates": [obj.dropoff_lon, obj.dropoff_lat]},
            ],
        }

    def get_summary(self, obj):
        return {
            "total_distance_miles":  obj.total_distance_miles,
            "total_driving_hours":   obj.total_driving_hours,
            "trip_duration_hours":   obj.trip_duration_hours,
            "total_days":            obj.total_days,
            "cycle_hours_before":    obj.current_cycle_used,
            "cycle_hours_after":     obj.cycle_hours_after,
            "cycle_hours_remaining": round(70.0 - (obj.cycle_hours_after or 0), 2),
            "num_rest_stops":        obj.num_rest_stops,
            "num_fuel_stops":        obj.num_fuel_stops,
            "num_breaks":            obj.num_breaks,
        }


class TripListSerializer(serializers.ModelSerializer):
    """Lightweight trip summary — used by GET /api/trips/"""

    class Meta:
        model  = Trip
        fields = [
            "id", "current_location", "pickup_location", "dropoff_location",
            "total_distance_miles", "total_days", "created_at",
        ]