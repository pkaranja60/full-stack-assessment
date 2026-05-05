from django.contrib import admin
from .models import Trip, TripStop, TripSegment, DailyLog, DailyLogSegment


class TripStopInline(admin.TabularInline):
    model  = TripStop
    extra  = 0
    fields = ("stop_type", "location", "time_label", "duration_hours", "description")
    readonly_fields = fields


class DailyLogInline(admin.TabularInline):
    model   = DailyLog
    extra   = 0
    fields  = ("day", "label", "total_driving", "total_on_duty_not_driving",
               "total_off_duty", "total_sleeper_berth")
    readonly_fields = fields


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display  = ("id", "current_location", "pickup_location", "dropoff_location",
                     "total_distance_miles", "total_days", "created_at")
    list_filter   = ("total_days", "created_at")
    search_fields = ("current_location", "pickup_location", "dropoff_location")
    readonly_fields = ("id", "created_at")
    inlines       = [TripStopInline, DailyLogInline]


class DailyLogSegmentInline(admin.TabularInline):
    model   = DailyLogSegment
    extra   = 0
    fields  = ("status", "start_time", "end_time", "duration", "description", "location")
    readonly_fields = fields


@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display  = ("trip", "day", "label", "total_driving",
                     "total_on_duty_not_driving", "total_off_duty")
    list_filter   = ("day",)
    inlines       = [DailyLogSegmentInline]


@admin.register(TripSegment)
class TripSegmentAdmin(admin.ModelAdmin):
    list_display  = ("trip", "day", "status", "start_time", "end_time", "duration", "miles")
    list_filter   = ("status", "day")


@admin.register(TripStop)
class TripStopAdmin(admin.ModelAdmin):
    list_display  = ("trip", "stop_type", "location", "time_label", "duration_hours")
    list_filter   = ("stop_type",)