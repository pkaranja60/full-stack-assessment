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
  - Driving window: 6 AM – 8 PM (nighttime rest enforced)
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
TRIP_START_HOUR      = 6.0     # 06:00 on Day 1 (hour 6 since midnight)

# Driving window (hardcoded for now — may become configurable later)
DRIVE_WINDOW_START   = 6.0     # 6 AM
DRIVE_WINDOW_END     = 20.0    # 8 PM


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
    cycle_after: float = 0.0
    cumulative_miles: float = 0.0   # total miles driven since trip start at segment end

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
    total_miles: float = 0.0       # cumulative miles driven since trip start


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


def _time_of_day(t: float) -> float:
    """Get the hour-of-day (0–24) from absolute time."""
    return t % 24


def _next_drivable_time(t: float) -> float:
    """
    Given an absolute time, return the next time that falls within the
    driving window [DRIVE_WINDOW_START, DRIVE_WINDOW_END].
    If already within the window, returns t unchanged.
    """
    tod = _time_of_day(t)
    if DRIVE_WINDOW_START <= tod < DRIVE_WINDOW_END:
        return t  # Already in the driving window
    # Outside the window — advance to next DRIVE_WINDOW_START
    if tod >= DRIVE_WINDOW_END:
        # Past evening cutoff — advance to next morning
        return t + (24 - tod) + DRIVE_WINDOW_START
    else:
        # Before morning start (e.g. 3 AM) — advance to this morning
        return t + (DRIVE_WINDOW_START - tod)


def _hours_until_window_end(t: float) -> float:
    """How many hours remain in the current driving window from time t."""
    tod = _time_of_day(t)
    if DRIVE_WINDOW_START <= tod < DRIVE_WINDOW_END:
        return DRIVE_WINDOW_END - tod
    return 0.0


def _insert_nighttime_rest(state: ShiftState, segments: List["Segment"], location: str) -> None:
    """
    If the current time is outside the driving window, insert an off-duty
    segment until the next drivable time and reset the shift.
    """
    next_t = _next_drivable_time(state.t)
    if next_t > state.t + 0.01:
        rest_duration = next_t - state.t
        segments.append(Segment(
            status="off_duty",
            start=state.t,
            end=next_t,
            description="Nighttime rest (off-duty until 6 AM)",
            location=location,
            cycle_after=state.cycle_used,
            cumulative_miles=state.total_miles,
        ))
        state.t = next_t
        # If rest was >= 10h, it counts as a full rest period — reset shift
        if rest_duration >= MIN_REST_HOURS - 0.01:
            state.shift_start = state.t
            state.shift_driving = 0.0
            state.shift_on_duty = 0.0
            state.cum_driving = 0.0


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
    Handles: nighttime rest, 30-min breaks, fuel stops, shift limits, 10-hr rests.
    """
    miles_left = miles_to_drive
    iters = 0

    while miles_left > 0.01:
        iters += 1
        if iters > max_iters:
            raise RuntimeError("HOS planner exceeded iteration limit — check inputs")

        # ── Enforce driving window ────────────────────────────────────────────
        rest_loc = f"Mile {state.total_miles:.0f} ({from_loc} → {to_loc})"
        _insert_nighttime_rest(state, segments, rest_loc)

        # ── How long can we keep driving before hitting a limit? ──────────────
        window_remaining  = (state.shift_start + MAX_WINDOW_HOURS) - state.t
        drive_remaining   = MAX_DRIVING_PER_SHIFT - state.shift_driving
        cycle_remaining   = CYCLE_LIMIT - state.cycle_used
        break_remaining   = BREAK_AFTER_HOURS - state.cum_driving
        daylight_remaining = _hours_until_window_end(state.t)

        available = min(window_remaining, drive_remaining, cycle_remaining, daylight_remaining)

        if available <= 0.01:
            if cycle_remaining <= 0.1:
                # ── 34-hour restart ───────────────────────────────────────────
                segments.append(Segment(
                    status="off_duty",
                    start=state.t,
                    end=state.t + 34.0,
                    description="34-hour restart (Cycle Reset)",
                    location=rest_loc,
                    cycle_after=0.0,
                    cumulative_miles=state.total_miles,
                ))
                state.t += 34.0
                state.shift_start   = state.t
                state.shift_driving = 0.0
                state.shift_on_duty = 0.0
                state.cum_driving   = 0.0
                state.cycle_used    = 0.0
                continue

            # ── Must rest (shift limit or window exhausted) ───────────────────
            segments.append(Segment(
                status="off_duty",
                start=state.t,
                end=state.t + MIN_REST_HOURS,
                description="Required 10-hour rest period",
                location=rest_loc,
                cycle_after=state.cycle_used,
                cumulative_miles=state.total_miles,
            ))
            state.t += MIN_REST_HOURS
            state.shift_start   = state.t
            state.shift_driving = 0.0
            state.shift_on_duty = 0.0
            state.cum_driving   = 0.0
            continue

        if state.cum_driving >= BREAK_AFTER_HOURS - 0.01:
            # ── 30-minute mandatory break ────────────────────────────────────
            segments.append(Segment(
                status="off_duty",
                start=state.t,
                end=state.t + BREAK_DURATION,
                description="30-minute required rest break",
                location=rest_loc,
                cycle_after=state.cycle_used,
                cumulative_miles=state.total_miles,
            ))
            state.t += BREAK_DURATION
            state.cum_driving = 0.0
            continue

        # ── Compute this drive segment ────────────────────────────────────────
        max_drive_before_break = min(available, break_remaining)

        miles_to_fuel = FUEL_INTERVAL_MILES - state.miles_since_fuel
        hours_to_fuel = miles_to_fuel / AVG_SPEED_MPH

        # Would we hit a fuel stop before running out of road?
        if miles_to_fuel < miles_left and hours_to_fuel < max_drive_before_break:
            drive_hrs  = hours_to_fuel
            drive_mi   = miles_to_fuel
            next_loc   = f"Mile {(state.total_miles + drive_mi):.0f} ({from_loc} → {to_loc})"
        else:
            max_mi     = min(miles_left, max_drive_before_break * AVG_SPEED_MPH)
            drive_mi   = max_mi
            drive_hrs  = drive_mi / AVG_SPEED_MPH
            next_loc   = to_loc if drive_mi >= miles_left - 0.01 else f"Mile {(state.total_miles + drive_mi):.0f} ({from_loc} → {to_loc})"

        if drive_hrs <= 0.001:
            # Edge case: almost no driving possible — force rest
            segments.append(Segment(
                status="off_duty",
                start=state.t,
                end=state.t + MIN_REST_HOURS,
                description="Required 10-hour rest period",
                location=from_loc,
                cycle_after=state.cycle_used,
                cumulative_miles=state.total_miles,
            ))
            state.t += MIN_REST_HOURS
            state.shift_start   = state.t
            state.shift_driving = 0.0
            state.shift_on_duty = 0.0
            state.cum_driving   = 0.0
            continue

        state.t                 += drive_hrs
        state.shift_driving     += drive_hrs
        state.shift_on_duty     += drive_hrs
        state.cum_driving       += drive_hrs
        state.cycle_used        += drive_hrs
        miles_left              -= drive_mi
        state.miles_since_fuel  += drive_mi
        state.total_miles       += drive_mi

        segments.append(Segment(
            status="driving",
            start=state.t - drive_hrs,
            end=state.t,
            description=f"Driving ({drive_mi:.0f} mi)",
            location=next_loc,
            miles=drive_mi,
            cycle_after=state.cycle_used,
            cumulative_miles=state.total_miles,
        ))

        # ── Fuel stop if we just reached the threshold ────────────────────────
        if state.miles_since_fuel >= FUEL_INTERVAL_MILES - 0.01 and miles_left > 0.01:
            fuel_loc = next_loc
            segments.append(Segment(
                status="on_duty_not_driving",
                start=state.t,
                end=state.t + FUEL_STOP_DURATION,
                description="Fuel stop",
                location=fuel_loc,
                cycle_after=state.cycle_used + FUEL_STOP_DURATION,
                cumulative_miles=state.total_miles,
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
                "cycle_after":  seg.cycle_after,
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
            "recap": {
                "cycle_hours_after": round(filled[-1].get("cycle_after", 0.0) if filled else 0.0, 2),
                "cycle_hours_remaining": round(max(0, CYCLE_LIMIT - (filled[-1].get("cycle_after", 0.0) if filled else 0.0)), 2),
            }
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
        "cycle_after": 0.0,
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

    # ── Prior duty block (if driver has prior cycle hours) ─────────────────────
    # Generate a solid block showing the prior on-duty time from previous trips.
    # This makes the 70hr cycle math self-documenting on the log sheets.
    if cycle_hours_used > 0:
        # Place prior duty at the start of the day (midnight to however many hours)
        prior_end = min(cycle_hours_used, TRIP_START_HOUR)  # Don't overlap with trip start
        if prior_end > 0.01:
            segments.append(Segment(
                status="on_duty_not_driving",
                start=0.0,
                end=prior_end,
                description=f"Prior duty from previous trips ({cycle_hours_used:.1f}h cycle used)",
                location=current_location,
                cycle_after=cycle_hours_used,
                cumulative_miles=0.0,
            ))

    # ── Pre-trip inspection ───────────────────────────────────────────────────
    segments.append(Segment(
        status="on_duty_not_driving",
        start=state.t,
        end=state.t + PRE_TRIP_DURATION,
        description="Pre-trip inspection",
        location=current_location,
        cycle_after=state.cycle_used + PRE_TRIP_DURATION,
        cumulative_miles=0.0,
    ))
    state.t             += PRE_TRIP_DURATION
    state.shift_on_duty += PRE_TRIP_DURATION
    state.cycle_used    += PRE_TRIP_DURATION

    # ── Leg 1: drive to pickup ────────────────────────────────────────────────
    if leg1_miles > 0.1:
        _drive_miles(leg1_miles, state, current_location, pickup_location, segments)

    # ── Pickup stop ───────────────────────────────────────────────────────────
    _insert_nighttime_rest(state, segments, pickup_location)
    # Ensure we have enough cycle/window to do the pickup work
    if (state.t - state.shift_start + PICKUP_DURATION > MAX_WINDOW_HOURS) or \
       (state.cycle_used + PICKUP_DURATION > CYCLE_LIMIT):
        rest_duration = 34.0 if state.cycle_used > CYCLE_LIMIT - 1.0 else MIN_REST_HOURS
        segments.append(Segment(
            status="off_duty",
            start=state.t,
            end=state.t + rest_duration,
            description="Rest before pickup" if rest_duration < 34 else "34-hour restart before pickup",
            location=pickup_location,
            cycle_after=0.0 if rest_duration >= 34 else state.cycle_used,
            cumulative_miles=state.total_miles,
        ))
        state.t += rest_duration
        state.shift_start = state.t
        state.shift_driving = 0.0
        state.shift_on_duty = 0.0
        state.cum_driving = 0.0
        if rest_duration >= 34:
            state.cycle_used = 0.0

    pickup_start = state.t
    segments.append(Segment(
        status="on_duty_not_driving",
        start=state.t,
        end=state.t + PICKUP_DURATION,
        description="Pickup — loading & paperwork",
        location=pickup_location,
        cycle_after=state.cycle_used + PICKUP_DURATION,
        cumulative_miles=state.total_miles,
    ))
    state.t             += PICKUP_DURATION
    state.shift_on_duty += PICKUP_DURATION
    state.cycle_used    += PICKUP_DURATION
    pickup_end = state.t

    # ── Leg 2: drive to dropoff ───────────────────────────────────────────────
    _drive_miles(leg2_miles, state, pickup_location, dropoff_location, segments)

    # ── Dropoff stop ──────────────────────────────────────────────────────────
    _insert_nighttime_rest(state, segments, dropoff_location)
    if (state.t - state.shift_start + DROPOFF_DURATION > MAX_WINDOW_HOURS) or \
       (state.cycle_used + DROPOFF_DURATION > CYCLE_LIMIT):
        rest_duration = 34.0 if state.cycle_used > CYCLE_LIMIT - 1.0 else MIN_REST_HOURS
        segments.append(Segment(
            status="off_duty",
            start=state.t,
            end=state.t + rest_duration,
            description="Rest before dropoff" if rest_duration < 34 else "34-hour restart before dropoff",
            location=dropoff_location,
            cycle_after=0.0 if rest_duration >= 34 else state.cycle_used,
            cumulative_miles=state.total_miles,
        ))
        state.t += rest_duration
        state.shift_start = state.t
        state.shift_driving = 0.0
        state.shift_on_duty = 0.0
        state.cum_driving = 0.0
        if rest_duration >= 34:
            state.cycle_used = 0.0

    dropoff_start = state.t
    segments.append(Segment(
        status="on_duty_not_driving",
        start=state.t,
        end=state.t + DROPOFF_DURATION,
        description="Dropoff — unloading & paperwork",
        location=dropoff_location,
        cycle_after=state.cycle_used + DROPOFF_DURATION,
        cumulative_miles=state.total_miles,
    ))
    state.t             += DROPOFF_DURATION
    state.cycle_used    += DROPOFF_DURATION
    dropoff_end = state.t

    # ── Build output ──────────────────────────────────────────────────────────
    daily_logs = _build_daily_logs(segments)

    # Stops list (for map display) — include cumulative_miles for interpolation
    stops = [
        {
            "stop_type":     "start",
            "location":      current_location,
            "hour_absolute": TRIP_START_HOUR,
            "time_label":    f"Day 1, {_hours_to_hhmm(TRIP_START_HOUR)}",
            "description":   "Trip start / pre-trip inspection",
            "cumulative_miles": 0.0,
        },
        {
            "stop_type":     "pickup",
            "location":      pickup_location,
            "hour_absolute": pickup_start,
            "time_label":    f"Day {_day_number(pickup_start)}, {_hours_to_hhmm(pickup_start % 24)}",
            "duration_hours": PICKUP_DURATION,
            "description":   "Pickup (1 hr on-duty)",
            "cumulative_miles": leg1_miles,
        },
        {
            "stop_type":     "dropoff",
            "location":      dropoff_location,
            "hour_absolute": dropoff_start,
            "time_label":    f"Day {_day_number(dropoff_start)}, {_hours_to_hhmm(dropoff_start % 24)}",
            "duration_hours": DROPOFF_DURATION,
            "description":   "Dropoff (1 hr on-duty)",
            "cumulative_miles": leg1_miles + leg2_miles,
        },
    ]

    # Add fuel stops from segments
    for seg in segments:
        if seg.description == "Fuel stop":
            stops.append({
                "stop_type":     "fuel",
                "location":      seg.location,
                "hour_absolute": seg.start,
                "time_label":    f"Day {_day_number(seg.start)}, {_hours_to_hhmm(seg.start % 24)}",
                "duration_hours": FUEL_STOP_DURATION,
                "description":   f"Fuel stop (30 min) — mile {seg.cumulative_miles:.0f}",
                "cumulative_miles": seg.cumulative_miles,
            })

    # Add rest stops (10-hour mandatory rest)
    for seg in segments:
        if seg.status == "off_duty" and seg.duration >= MIN_REST_HOURS - 0.01:
            stops.append({
                "stop_type":     "rest",
                "location":      seg.location,
                "hour_absolute": seg.start,
                "time_label":    f"Day {_day_number(seg.start)}, {_hours_to_hhmm(seg.start % 24)}",
                "duration_hours": seg.duration,
                "description":   f"Required {seg.duration:.0f}h rest — mile {seg.cumulative_miles:.0f}",
                "cumulative_miles": seg.cumulative_miles,
            })

    # Add 30-minute breaks to the stops list for map display
    for seg in segments:
        if "30-minute" in seg.description:
            stops.append({
                "stop_type":     "break",
                "location":      seg.location,
                "hour_absolute": seg.start,
                "time_label":    f"Day {_day_number(seg.start)}, {_hours_to_hhmm(seg.start % 24)}",
                "duration_hours": BREAK_DURATION,
                "description":   f"30-min break — mile {seg.cumulative_miles:.0f}",
                "cumulative_miles": seg.cumulative_miles,
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