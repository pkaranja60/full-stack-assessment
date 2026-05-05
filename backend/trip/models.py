from django.db import models
import uuid


class Trip(models.Model):
    """Stores the input and high-level summary of a planned trip."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ── Inputs ────────────────────────────────────────────────────────────────
    current_location   = models.CharField(max_length=300)
    pickup_location    = models.CharField(max_length=300)
    dropoff_location   = models.CharField(max_length=300)
    current_cycle_used = models.FloatField(help_text="Hours used in current 70-hr/8-day cycle")

    # ── Route info (from OSRM) ────────────────────────────────────────────────
    total_distance_miles   = models.FloatField(null=True, blank=True)
    total_duration_hours   = models.FloatField(null=True, blank=True)
    route_geometry         = models.JSONField(null=True, blank=True,
                                              help_text="GeoJSON LineString for map display")

    # ── Coordinates (from Nominatim) ──────────────────────────────────────────
    current_lat  = models.FloatField(null=True, blank=True)
    current_lon  = models.FloatField(null=True, blank=True)
    pickup_lat   = models.FloatField(null=True, blank=True)
    pickup_lon   = models.FloatField(null=True, blank=True)
    dropoff_lat  = models.FloatField(null=True, blank=True)
    dropoff_lon  = models.FloatField(null=True, blank=True)

    # ── HOS summary ───────────────────────────────────────────────────────────
    total_driving_hours    = models.FloatField(null=True, blank=True)
    trip_duration_hours    = models.FloatField(null=True, blank=True)
    total_days             = models.IntegerField(null=True, blank=True)
    cycle_hours_after      = models.FloatField(null=True, blank=True)
    num_rest_stops         = models.IntegerField(default=0)
    num_fuel_stops         = models.IntegerField(default=0)
    num_breaks             = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Trip {self.id} | {self.current_location} → {self.dropoff_location}"


class TripStop(models.Model):
    """Ordered stops along the trip (start, pickup, fuel, rest, dropoff)."""

    STOP_TYPES = [
        ("start",   "Trip Start"),
        ("pickup",  "Pickup"),
        ("fuel",    "Fuel Stop"),
        ("rest",    "Rest Stop"),
        ("break",   "30-Min Break"),
        ("dropoff", "Dropoff"),
    ]

    trip        = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="stops")
    stop_type   = models.CharField(max_length=20, choices=STOP_TYPES)
    location    = models.CharField(max_length=300)
    lat         = models.FloatField(null=True, blank=True)
    lon         = models.FloatField(null=True, blank=True)

    hour_absolute  = models.FloatField(help_text="Hours since trip Day 1 midnight")
    time_label     = models.CharField(max_length=50)
    duration_hours = models.FloatField(default=0.0)
    description    = models.CharField(max_length=255, blank=True)
    order          = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "hour_absolute"]

    def __str__(self):
        return f"{self.stop_type} @ {self.location} ({self.time_label})"


class TripSegment(models.Model):
    """
    One duty-status block (driving, off_duty, on_duty_not_driving, sleeper_berth).
    Flat list for the whole trip — used for rendering and analysis.
    """

    STATUS_CHOICES = [
        ("driving",             "Driving"),
        ("off_duty",            "Off Duty"),
        ("on_duty_not_driving", "On Duty (Not Driving)"),
        ("sleeper_berth",       "Sleeper Berth"),
    ]

    trip        = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="segments")
    status      = models.CharField(max_length=30, choices=STATUS_CHOICES)
    start       = models.FloatField(help_text="Hours since trip Day 1 midnight")
    end         = models.FloatField(help_text="Hours since trip Day 1 midnight")
    duration    = models.FloatField()
    description = models.CharField(max_length=255, blank=True)
    location    = models.CharField(max_length=300, blank=True)
    miles       = models.FloatField(default=0.0)
    day         = models.IntegerField(help_text="Which day of the trip (1-indexed)")
    start_time  = models.CharField(max_length=10, help_text="HH:MM within the day")
    end_time    = models.CharField(max_length=10, help_text="HH:MM within the day")

    class Meta:
        ordering = ["start"]

    def __str__(self):
        return f"Day {self.day} {self.start_time}-{self.end_time} [{self.status}]"


class DailyLog(models.Model):
    """One 24-hour ELD log sheet."""

    trip      = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="daily_logs")
    day       = models.IntegerField(help_text="Day number (1-indexed)")
    label     = models.CharField(max_length=50)

    # Totals for the day (hours)
    total_off_duty            = models.FloatField(default=0.0)
    total_sleeper_berth       = models.FloatField(default=0.0)
    total_driving             = models.FloatField(default=0.0)
    total_on_duty_not_driving = models.FloatField(default=0.0)
    
    # Recap info for the day
    cycle_hours_after      = models.FloatField(null=True, blank=True)
    cycle_hours_remaining  = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["day"]
        unique_together = [("trip", "day")]

    def __str__(self):
        return f"Trip {self.trip_id} — Day {self.day} log"


class DailyLogSegment(models.Model):
    """
    One duty-status block within a single DailyLog (clipped to that 24-hour window).
    These are what get drawn on the log sheet grid.
    """

    STATUS_CHOICES = [
        ("driving",             "Driving"),
        ("off_duty",            "Off Duty"),
        ("on_duty_not_driving", "On Duty (Not Driving)"),
        ("sleeper_berth",       "Sleeper Berth"),
    ]

    daily_log   = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name="segments")
    status      = models.CharField(max_length=30, choices=STATUS_CHOICES)
    start_hour  = models.FloatField(help_text="Hours since midnight of this day (0–24)")
    end_hour    = models.FloatField(help_text="Hours since midnight of this day (0–24)")
    duration    = models.FloatField()
    description = models.CharField(max_length=255, blank=True)
    location    = models.CharField(max_length=300, blank=True)
    start_time  = models.CharField(max_length=10)
    end_time    = models.CharField(max_length=10)

    class Meta:
        ordering = ["start_hour"]

    def __str__(self):
        return f"Day {self.daily_log.day} {self.start_time}-{self.end_time} [{self.status}]"