"""
HOS (Hours of Service) Calculator for Property-Carrying CMV Drivers.

Rules applied (FMCSA 49 CFR Part 395):
  - 11-hour driving limit per shift
  - 14-hour driving window from shift start
  - 10 consecutive hours off duty between shifts
  - 30-minute break required after 8 cumulative driving hours
  - 70-hour / 8-day cycle limit
  - Fuel stop every 1,000 miles (30 min on-duty)
  - 1-hour on-duty (not driving) at pickup and dropoff
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple

# ── Constants ────────────────────────────────────────────────────────────────

AVG_SPEED_MPH        = 55.0
MAX_DRIVING_PER_SHIFT = 11.0   # hours
MAX_WINDOW_HOURS     = 14.0    # hours from shift start
MIN_REST_HOURS       = 10.0    # consecutive off-duty required
BREAK_AFTER_HOURS    = 8.0     # cumulative driving before mandatory 30-min break
BREAK_DURATION       = 0.5     # 30 minutes
CYCLE_LIMIT          = 70.0    # hours in 8-day rolling period
FUEL_INTERVAL_MILES  = 1000.0
FUEL_STOP_DURATION   = 0.5     # 30 minutes
PICKUP_DURATION      = 1.0     # 1 hour on-duty
DROPOFF_DURATION     = 1.0     # 1 hour on-duty
PRE_TRIP_DURATION    = 0.5     # 30-min pre-trip inspection
TRIP_START_HOUR      = 8.0     # 08:00 on Day 1 (hour 8 since midnight)


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class Segment:
    """One continuous block of the same duty status."""
    status: str          # driving | on_duty_not_driving | off_duty | sleeper_berth
    start: float         # hours since midnight of Day 1
    end: float
    description: str
    location: str = ""
    miles: float = 0.0

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 4)


@dataclass
class ShiftState:
    """Mutable shift-tracking state passed through the planner."""
    t: float                        # current time (hours since midnight Day 1)
    shift_start: float              # time current shift began
    shift_driving: float = 0.0     # driving hours this shift
    shift_on_duty: float = 0.0     # total on-duty hours this shift (driving + not-driving)
    cum_driving: float = 0.0       # cumulative driving since last 30-min break
    cycle_used: float = 0.0        # cycle hours used (rolling 8-day)
    miles_since_fuel: float = 0.0


# ── Helpers ──────────────────────────────────────────────────────────────────

def _hours_to_hhmm(hours: float) -> str:
    """Convert decimal hours to HH:MM string (e.g. 8.5 → '08:30')."""
    h = int(hours) % 24
    m = int(round((hours % 1) * 60))
    if m == 60:
        h += 1
        m = 0
    return f"{h:02d}:{m:02d}"


def _day_number(t: float) -> int:
    return int(t // 24) + 1


# ── Core driving engine ──────────────────────────────────────────────────────

def _drive_miles(
    miles_to_drive: float,
    state: ShiftState,
    from_loc: str,
    to_loc: str,
    segments: List[Segment],
    max_iters: int = 500,
) -> None:
    """
    Drive `miles_to_drive` miles, emitting Segment objects and mutating `state`.
    Handles: 30-min breaks, fuel stops, shift limits, 10-hr rests.
    """
    miles_left = miles_to_drive
    iters = 0

    while miles_left > 0.01:
        iters += 1
        if iters > max_iters:
            raise RuntimeError("HOS planner exceeded iteration limit — check inputs")

        # ── How long can we keep driving before hitting a limit? ──────────────
        window_remaining  = (state.shift_start + MAX_WINDOW_HOURS) - state.t
        drive_remaining   = MAX_DRIVING_PER_SHIFT - state.shift_driving
        cycle_remaining   = CYCLE_LIMIT - state.cycle_used
        break_remaining   = BREAK_AFTER_HOURS - state.cum_driving  # until next mandatory break

        available = min(window_remaining, drive_remaining, cycle_remaining)

        if available <= 0.01:
            # ── Must rest ────────────────────────────────────────────────────
            rest_loc = from_loc if miles_left >= miles_to_drive else to_loc
            segments.append(Segment(
                status="off_duty",
                start=state.t,
                end=state.t + MIN_REST_HOURS,
                description="Required 10-hour rest period",
                location=rest_loc,
            ))
            state.t += MIN_REST_HOURS
            state.shift_start   = state.t
            state.shift_driving = 0.0
            state.shift_on_duty = 0.0
            state.cum_driving   = 0.0
            continue

        if state.cum_driving >= BREAK_AFTER_HOURS - 0.01:
            # ── 30-minute mandatory break ────────────────────────────────────
            rest_loc = from_loc if miles_left >= miles_to_drive else to_loc
            segments.append(Segment(
                status="off_duty",
                start=state.t,
                end=state.t + BREAK_DURATION,
                description="30-minute required rest break",
                location=rest_loc,
            ))
            state.t += BREAK_DURATION
            state.cum_driving = 0.0
            # Break consumes window time but is off-duty (not driving/on-duty)
            continue

        # ── Compute this drive segment ────────────────────────────────────────
        # Cap by: break requirement, HOS limits, remaining miles, fuel interval
        max_drive_before_break = min(available, break_remaining)

        miles_to_fuel = FUEL_INTERVAL_MILES - state.miles_since_fuel
        hours_to_fuel = miles_to_fuel / AVG_SPEED_MPH

        # Would we hit a fuel stop before running out of road?
        if miles_to_fuel < miles_left and hours_to_fuel < max_drive_before_break:
            # Drive to fuel stop
            drive_hrs  = hours_to_fuel
            drive_mi   = miles_to_fuel
            next_loc   = f"Fuel stop near {to_loc}"
        else:
            # Drive as far as possible
            max_mi     = min(miles_left, max_drive_before_break * AVG_SPEED_MPH)
            drive_mi   = max_mi
            drive_hrs  = drive_mi / AVG_SPEED_MPH
            next_loc   = to_loc if drive_mi >= miles_left else from_loc

        if drive_hrs <= 0.001:
            # Edge case: almost no driving possible — force rest
            segments.append(Segment(
                status="off_duty",
                start=state.t,
                end=state.t + MIN_REST_HOURS,
                description="Required 10-hour rest period",
                location=from_loc,
            ))
            state.t += MIN_REST_HOURS
            state.shift_start   = state.t
            state.shift_driving = 0.0
            state.shift_on_duty = 0.0
            state.cum_driving   = 0.0
            continue

        segments.append(Segment(
            status="driving",
            start=state.t,
            end=state.t + drive_hrs,
            description=f"Driving ({drive_mi:.0f} mi)",
            location=next_loc,
            miles=drive_mi,
        ))
        state.t                 += drive_hrs
        state.shift_driving     += drive_hrs
        state.shift_on_duty     += drive_hrs
        state.cum_driving       += drive_hrs
        state.cycle_used        += drive_hrs
        miles_left              -= drive_mi
        state.miles_since_fuel  += drive_mi

        # ── Fuel stop if we just reached the threshold ────────────────────────
        if state.miles_since_fuel >= FUEL_INTERVAL_MILES - 0.01 and miles_left > 0.01:
            fuel_loc = next_loc
            segments.append(Segment(
                status="on_duty_not_driving",
                start=state.t,
                end=state.t + FUEL_STOP_DURATION,
                description="Fuel stop",
                location=fuel_loc,
            ))
            state.t                 += FUEL_STOP_DURATION
            state.shift_on_duty     += FUEL_STOP_DURATION
            state.cycle_used        += FUEL_STOP_DURATION
            state.miles_since_fuel   = 0.0


# ── Daily log builder ────────────────────────────────────────────────────────

def _build_daily_logs(segments: List[Segment]) -> List[dict]:
    """
    Split flat segment list into per-24-hour log sheets.
    Gaps are filled with off-duty time.
    """
    if not segments:
        return []

    trip_end = segments[-1].end
    total_days = math.ceil(trip_end / 24)

    # Ensure total_days is at least 1
    total_days = max(total_days, 1)

    daily_logs = []

    for day in range(1, total_days + 1):
        day_start = (day - 1) * 24.0
        day_end   = day * 24.0

        raw: List[dict] = []

        for seg in segments:
            if seg.end <= day_start or seg.start >= day_end:
                continue
            clip_start = max(seg.start, day_start)
            clip_end   = min(seg.end,   day_end)
            raw.append({
                "status":       seg.status,
                "start_hour":   round(clip_start - day_start, 4),
                "end_hour":     round(clip_end   - day_start, 4),
                "duration":     round(clip_end - clip_start,  4),
                "description":  seg.description,
                "location":     seg.location,
                "start_time":   _hours_to_hhmm(clip_start - day_start),
                "end_time":     _hours_to_hhmm(clip_end   - day_start),
            })

        # Sort and fill gaps with off_duty
        raw.sort(key=lambda s: s["start_hour"])
        filled = _fill_gaps(raw)

        # Totals
        totals = {
            "off_duty":            0.0,
            "sleeper_berth":       0.0,
            "driving":             0.0,
            "on_duty_not_driving": 0.0,
        }
        for s in filled:
            key = s["status"]
            if key in totals:
                totals[key] = round(totals[key] + s["duration"], 4)

        daily_logs.append({
            "day":      day,
            "label":    f"Day {day}",
            "segments": filled,
            "totals":   totals,
        })

    return daily_logs


def _fill_gaps(segments: List[dict]) -> List[dict]:
    """Insert off-duty blocks wherever there is a gap in a 24-hour day."""
    if not segments:
        return [_off_duty_block(0, 24, "Off duty")]

    result = []
    cursor = 0.0

    for seg in segments:
        if seg["start_hour"] > cursor + 0.01:
            result.append(_off_duty_block(cursor, seg["start_hour"], "Off duty"))
        result.append(seg)
        cursor = seg["end_hour"]

    if cursor < 24.0 - 0.01:
        result.append(_off_duty_block(cursor, 24.0, "Off duty"))

    return result


def _off_duty_block(start: float, end: float, desc: str) -> dict:
    return {
        "status":      "off_duty",
        "start_hour":  round(start, 4),
        "end_hour":    round(end,   4),
        "duration":    round(end - start, 4),
        "description": desc,
        "location":    "",
        "start_time":  _hours_to_hhmm(start),
        "end_time":    _hours_to_hhmm(end),
    }


# ── Public API ───────────────────────────────────────────────────────────────

def plan_trip(
    leg1_miles: float,   # current_location → pickup
    leg2_miles: float,   # pickup → dropoff
    cycle_hours_used: float,
    current_location: str,
    pickup_location: str,
    dropoff_location: str,
) -> dict:
    """
    Plan a full trip and return structured schedule + daily ELD logs.

    Args:
        leg1_miles:        Road miles from current location to pickup.
        leg2_miles:        Road miles from pickup to dropoff.
        cycle_hours_used:  Hours already used in the current 70-hr/8-day cycle.
        current_location:  Human-readable name of current location.
        pickup_location:   Human-readable name of pickup location.
        dropoff_location:  Human-readable name of dropoff location.

    Returns:
        dict with keys: segments, daily_logs, stops, summary
    """
    segments: List[Segment] = []

    state = ShiftState(
        t=TRIP_START_HOUR,
        shift_start=TRIP_START_HOUR,
        cycle_used=cycle_hours_used,
    )

    # ── Pre-trip inspection ───────────────────────────────────────────────────
    segments.append(Segment(
        status="on_duty_not_driving",
        start=state.t,
        end=state.t + PRE_TRIP_DURATION,
        description="Pre-trip inspection",
        location=current_location,
    ))
    state.t             += PRE_TRIP_DURATION
    state.shift_on_duty += PRE_TRIP_DURATION
    state.cycle_used    += PRE_TRIP_DURATION

    # ── Leg 1: drive to pickup ────────────────────────────────────────────────
    if leg1_miles > 0.1:
        _drive_miles(leg1_miles, state, current_location, pickup_location, segments)

    # ── Pickup stop ───────────────────────────────────────────────────────────
    pickup_start = state.t
    segments.append(Segment(
        status="on_duty_not_driving",
        start=state.t,
        end=state.t + PICKUP_DURATION,
        description="Pickup — loading & paperwork",
        location=pickup_location,
    ))
    state.t             += PICKUP_DURATION
    state.shift_on_duty += PICKUP_DURATION
    state.cycle_used    += PICKUP_DURATION
    pickup_end = state.t

    # ── Leg 2: drive to dropoff ───────────────────────────────────────────────
    _drive_miles(leg2_miles, state, pickup_location, dropoff_location, segments)

    # ── Dropoff stop ──────────────────────────────────────────────────────────
    dropoff_start = state.t
    segments.append(Segment(
        status="on_duty_not_driving",
        start=state.t,
        end=state.t + DROPOFF_DURATION,
        description="Dropoff — unloading & paperwork",
        location=dropoff_location,
    ))
    state.t             += DROPOFF_DURATION
    state.cycle_used    += DROPOFF_DURATION
    dropoff_end = state.t

    # ── Build output ──────────────────────────────────────────────────────────
    daily_logs = _build_daily_logs(segments)

    # Stops list (for map display)
    stops = [
        {
            "type":          "start",
            "location":      current_location,
            "hour_absolute": TRIP_START_HOUR,
            "time_label":    f"Day 1, {_hours_to_hhmm(TRIP_START_HOUR)}",
            "description":   "Trip start / pre-trip inspection",
        },
        {
            "type":          "pickup",
            "location":      pickup_location,
            "hour_absolute": pickup_start,
            "time_label":    f"Day {_day_number(pickup_start)}, {_hours_to_hhmm(pickup_start % 24)}",
            "duration_hours": PICKUP_DURATION,
            "description":   "Pickup (1 hr on-duty)",
        },
        {
            "type":          "dropoff",
            "location":      dropoff_location,
            "hour_absolute": dropoff_start,
            "time_label":    f"Day {_day_number(dropoff_start)}, {_hours_to_hhmm(dropoff_start % 24)}",
            "duration_hours": DROPOFF_DURATION,
            "description":   "Dropoff (1 hr on-duty)",
        },
    ]

    # Add fuel stops from segments
    for seg in segments:
        if seg.description == "Fuel stop":
            stops.append({
                "type":          "fuel",
                "location":      seg.location,
                "hour_absolute": seg.start,
                "time_label":    f"Day {_day_number(seg.start)}, {_hours_to_hhmm(seg.start % 24)}",
                "duration_hours": FUEL_STOP_DURATION,
                "description":   "Fuel stop (30 min)",
            })

    # Add rest stops
    for seg in segments:
        if seg.status == "off_duty" and seg.duration >= MIN_REST_HOURS - 0.01:
            stops.append({
                "type":          "rest",
                "location":      seg.location,
                "hour_absolute": seg.start,
                "time_label":    f"Day {_day_number(seg.start)}, {_hours_to_hhmm(seg.start % 24)}",
                "duration_hours": seg.duration,
                "description":   f"Required rest ({seg.duration:.1f} hrs)",
            })

    stops.sort(key=lambda s: s["hour_absolute"])

    # Summary
    total_driving = sum(s.miles for s in segments if s.status == "driving")
    total_driving_hrs = sum(s.duration for s in segments if s.status == "driving")
    trip_duration_hrs = dropoff_end - TRIP_START_HOUR

    summary = {
        "total_distance_miles":  round(total_driving, 1),
        "total_driving_hours":   round(total_driving_hrs, 2),
        "trip_duration_hours":   round(trip_duration_hrs, 2),
        "total_days":            len(daily_logs),
        "cycle_hours_before":    round(cycle_hours_used, 2),
        "cycle_hours_after":     round(state.cycle_used, 2),
        "cycle_hours_remaining": round(CYCLE_LIMIT - state.cycle_used, 2),
        "num_rest_stops":        sum(1 for s in segments if s.status == "off_duty" and s.duration >= MIN_REST_HOURS - 0.01),
        "num_fuel_stops":        sum(1 for s in segments if s.description == "Fuel stop"),
        "num_breaks":            sum(1 for s in segments if "30-minute" in s.description),
    }

    # Serialize segments for API response
    serialized_segments = [
        {
            "status":      s.status,
            "start":       round(s.start, 4),
            "end":         round(s.end,   4),
            "duration":    round(s.duration, 4),
            "description": s.description,
            "location":    s.location,
            "miles":       round(s.miles, 2),
            "day":         _day_number(s.start),
            "start_time":  _hours_to_hhmm(s.start % 24),
            "end_time":    _hours_to_hhmm(s.end   % 24),
        }
        for s in segments
    ]

    return {
        "segments":   serialized_segments,
        "daily_logs": daily_logs,
        "stops":      stops,
        "summary":    summary,
    }