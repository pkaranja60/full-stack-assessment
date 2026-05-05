"""
ELD Log Sheet Generator — draws a completed Driver's Daily Log using Pillow.

Produces a high-resolution PNG that matches the FMCSA paper log format:
  - Header  : date, carrier, driver, truck, mileage
  - Grid    : 24-hour timeline with minute-precision tick marks
  - Rows    : Off Duty / Sleeper Berth / Driving / On Duty (Not Driving)
  - Duty lines drawn from daily-log segment data
  - Remarks : location / status-change notes
  - Totals  : hours per duty status (must sum to 24)
"""

from __future__ import annotations

import io
import textwrap
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

# ── Canvas dimensions (landscape, ~letter at 150 dpi) ────────────────────────
W, H          = 1650, 1100
MARGIN_LEFT   = 20
MARGIN_RIGHT  = 20
MARGIN_TOP    = 20

# ── Colour palette ────────────────────────────────────────────────────────────
WHITE  = (255, 255, 255)
BLACK  = (0,   0,   0)
GRAY   = (180, 180, 180)
LGRAY  = (230, 230, 230)

STATUS_COLORS = {
    "off_duty":            (70,  130, 180),   # steel-blue
    "sleeper_berth":       (100, 160, 100),   # muted-green
    "driving":             (220,  80,  60),   # red-orange
    "on_duty_not_driving": (230, 160,  30),   # amber
}

# ── Layout constants ──────────────────────────────────────────────────────────
HEADER_H      = 230          # height of the header block
GRID_TOP      = HEADER_TOP = MARGIN_TOP + HEADER_H + 10
TICK_HEADER_H = 36           # hour-label + tick row height
ROW_H         = 38           # height of each duty-status row
NUM_ROWS      = 4
GRID_H        = TICK_HEADER_H + NUM_ROWS * ROW_H + 2   # total grid height

LABEL_W       = 130          # left label column ("1. Off Duty" etc.)
TOTAL_W       = 70           # right total-hours column
GRID_LEFT     = MARGIN_LEFT  + LABEL_W
GRID_RIGHT    = W - MARGIN_RIGHT - TOTAL_W
GRID_W        = GRID_RIGHT - GRID_LEFT                  # drawable width = 24h span

REMARKS_TOP   = GRID_TOP + GRID_H + 16
REMARKS_H     = 180
RECAP_TOP     = REMARKS_TOP + REMARKS_H + 16

HOUR_W        = GRID_W / 24.0           # pixels per hour
MINUTE_W      = HOUR_W / 60.0          # pixels per minute

# Duty-status row order and labels
STATUSES = [
    ("off_duty",            "1. Off Duty"),
    ("sleeper_berth",       "2. Sleeper\n   Berth"),
    ("driving",             "3. Driving"),
    ("on_duty_not_driving", "4. On Duty\n   (Not Driving)"),
]

# ── Font loading ──────────────────────────────────────────────────────────────

def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Try to load a TrueType font; fall back to the default bitmap font."""
    candidates = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


# ── Coordinate helpers ────────────────────────────────────────────────────────

def _x_for_hour(hour: float) -> int:
    """Convert a decimal hour (0–24) to an x-pixel coordinate in the grid."""
    return int(GRID_LEFT + hour * HOUR_W)


def _row_y(row_index: int) -> int:
    """Top y of a duty-status row (0=Off Duty … 3=On Duty Not Driving)."""
    return GRID_TOP + TICK_HEADER_H + row_index * ROW_H


# ── Sub-drawing routines ──────────────────────────────────────────────────────

def _draw_header(draw: ImageDraw.Draw, data: dict) -> None:
    """Draw the top header block: title, date, driver info, carrier info."""
    f_title  = _load_font(22, bold=True)
    f_large  = _load_font(16, bold=True)
    f_normal = _load_font(13)
    f_small  = _load_font(11)

    # Title
    draw.text((MARGIN_LEFT, MARGIN_TOP), "Drivers Daily Log", font=f_title, fill=BLACK)
    draw.text((MARGIN_LEFT, MARGIN_TOP + 26), "(24 hours)", font=f_small, fill=BLACK)

    # Original / duplicate note
    note = "Original - File at home terminal.\nDuplicate - Driver retains in his/her possession for 8 days."
    draw.text((W // 2, MARGIN_TOP), note, font=f_small, fill=BLACK)

    # Date line
    date_str = data.get("date", "___/___/______")
    draw.text((350, MARGIN_TOP + 4), date_str, font=f_large, fill=BLACK)
    draw.text((290, MARGIN_TOP + 20), "(month)", font=f_small, fill=GRAY)
    draw.text((370, MARGIN_TOP + 20), "(day)", font=f_small, fill=GRAY)
    draw.text((430, MARGIN_TOP + 20), "(year)", font=f_small, fill=GRAY)

    # From / To
    draw.text((MARGIN_LEFT, MARGIN_TOP + 52), "From:", font=f_normal, fill=BLACK)
    draw.text((MARGIN_LEFT, MARGIN_TOP + 72), data.get("from_location", ""), font=f_normal, fill=BLACK)
    draw.text((W // 2, MARGIN_TOP + 52), "To:", font=f_normal, fill=BLACK)
    draw.text((W // 2 + 30, MARGIN_TOP + 52), data.get("to_location", ""), font=f_normal, fill=BLACK)

    # Mileage boxes
    box_y = MARGIN_TOP + 90
    for bx, label, val in [
        (MARGIN_LEFT, "Total Miles Driving Today", data.get("total_miles", "")),
        (MARGIN_LEFT + 200, "Total Mileage Today",     data.get("total_mileage", "")),
    ]:
        draw.rectangle([bx, box_y, bx + 160, box_y + 40], outline=BLACK, width=1)
        draw.text((bx + 4, box_y + 4), str(val), font=f_large, fill=BLACK)
        draw.text((bx, box_y + 44), label, font=f_small, fill=BLACK)

    # Truck / trailer
    draw.text((MARGIN_LEFT, box_y + 68),
              data.get("truck_numbers", "Truck/Tractor and Trailer Numbers or License Plates/State"),
              font=f_small, fill=BLACK)

    # Carrier block (right side)
    cx = W // 2
    for cy, label, val in [
        (MARGIN_TOP + 90,  "Name of Carrier or Carriers", data.get("carrier_name", "")),
        (MARGIN_TOP + 130, "Main Office Address",          data.get("main_office", "")),
        (MARGIN_TOP + 170, "Home Terminal Address",        data.get("home_terminal", "")),
    ]:
        draw.line([(cx, cy + 20), (W - MARGIN_RIGHT, cy + 20)], fill=BLACK, width=1)
        draw.text((cx, cy + 22), label, font=f_small, fill=GRAY)
        draw.text((cx, cy + 4),  val,   font=f_normal, fill=BLACK)

    # Driver signature / co-driver
    sig_y = MARGIN_TOP + 195
    draw.line([(MARGIN_LEFT, sig_y + 20), (W // 2 - 20, sig_y + 20)], fill=BLACK, width=1)
    draw.text((MARGIN_LEFT, sig_y + 22), "Driver's Signature in Full", font=f_small, fill=GRAY)
    draw.text((MARGIN_LEFT, sig_y + 4),  data.get("driver_name", ""), font=f_normal, fill=BLACK)

    draw.line([(W // 2, sig_y + 20), (W - 200, sig_y + 20)], fill=BLACK, width=1)
    draw.text((W // 2, sig_y + 22), "Name of Co-Driver", font=f_small, fill=GRAY)
    draw.text((W // 2, sig_y + 4),  data.get("co_driver", ""), font=f_normal, fill=BLACK)

    # Horizontal divider below header
    draw.line([(MARGIN_LEFT, GRID_TOP - 6), (W - MARGIN_RIGHT, GRID_TOP - 6)], fill=BLACK, width=2)


def _draw_grid_skeleton(draw: ImageDraw.Draw) -> None:
    """Draw the empty 24-hour grid: hour labels, tick marks, row borders."""
    f_hour  = _load_font(11, bold=True)
    f_small = _load_font(9)

    tick_top    = GRID_TOP
    tick_bottom = GRID_TOP + TICK_HEADER_H
    grid_bottom = GRID_TOP + GRID_H

    # Outer border of the entire grid
    draw.rectangle(
        [GRID_LEFT, GRID_TOP, GRID_RIGHT, grid_bottom],
        outline=BLACK, width=2,
    )

    # Hour columns + labels
    hours = list(range(0, 25))
    for h in hours:
        x = _x_for_hour(h)

        # Major tick (every hour)
        draw.line([(x, tick_top), (x, tick_bottom)], fill=BLACK, width=1)

        # Hour label
        if h == 0:
            label = "Mid-\nnight"
        elif h == 12:
            label = "Noon"
        elif h == 24:
            label = "Mid-\nnight"
        else:
            label = str(h)

        if "\n" in label:
            parts = label.split("\n")
            draw.text((x + 2, tick_top + 2),  parts[0], font=f_small, fill=BLACK)
            draw.text((x + 2, tick_top + 13), parts[1], font=f_small, fill=BLACK)
        else:
            draw.text((x + 2, tick_top + 6), label, font=f_hour, fill=BLACK)

        # Minor ticks (every 15 min) between full hours
        if h < 24:
            for q in [1, 2, 3]:
                qx = _x_for_hour(h + q / 4)
                tick_h = 8 if q == 2 else 5
                draw.line([(qx, tick_bottom - tick_h), (qx, tick_bottom)], fill=BLACK, width=1)

    # Horizontal line under tick header
    draw.line([(GRID_LEFT, tick_bottom), (GRID_RIGHT, tick_bottom)], fill=BLACK, width=1)

    # Row borders and left labels
    f_row = _load_font(11)
    for i, (_, label) in enumerate(STATUSES):
        row_y = _row_y(i)
        # Row separator line
        draw.line([(MARGIN_LEFT, row_y), (GRID_RIGHT, row_y)], fill=BLACK, width=1)
        # Label
        for li, line in enumerate(label.split("\n")):
            draw.text((MARGIN_LEFT, row_y + 4 + li * 13), line, font=f_row, fill=BLACK)
        # Light vertical guides at every hour within each row
        for h in range(1, 24):
            x = _x_for_hour(h)
            draw.line([(x, row_y), (x, row_y + ROW_H)], fill=LGRAY, width=1)

    # Bottom border of last row
    bottom_y = _row_y(NUM_ROWS)
    draw.line([(MARGIN_LEFT, bottom_y), (GRID_RIGHT, bottom_y)], fill=BLACK, width=2)

    # "Total Hours" column header
    f_th = _load_font(10)
    draw.text((GRID_RIGHT + 4, GRID_TOP + 4), "Total\nHours", font=f_th, fill=BLACK)


def _draw_duty_lines(draw: ImageDraw.Draw, segments: List[dict]) -> None:
    """Fill each duty-status row with thick colored lines for each segment."""
    LINE_THICKNESS = ROW_H - 10   # line fills most of the row height

    for seg in segments:
        status     = seg.get("status", "off_duty")
        start_hour = float(seg.get("start_hour", 0))
        end_hour   = float(seg.get("end_hour",   0))

        row_index = next(
            (i for i, (s, _) in enumerate(STATUSES) if s == status), 0
        )
        color = STATUS_COLORS.get(status, GRAY)

        x1   = _x_for_hour(start_hour)
        x2   = _x_for_hour(end_hour)
        row_y = _row_y(row_index)
        cy   = row_y + ROW_H // 2

        # Thick horizontal bar
        draw.rectangle(
            [x1 + 1, cy - LINE_THICKNESS // 2,
             x2 - 1, cy + LINE_THICKNESS // 2],
            fill=color,
        )

        # Vertical drop-lines at transitions (connect to next status visually)
        draw.line([(x1, row_y + 2), (x1, row_y + ROW_H - 2)], fill=color, width=2)
        draw.line([(x2, row_y + 2), (x2, row_y + ROW_H - 2)], fill=color, width=2)


def _draw_totals(draw: ImageDraw.Draw, totals: dict) -> None:
    """Write per-row hour totals in the right column."""
    f_total = _load_font(12, bold=True)
    grand   = 0.0

    for i, (status, _) in enumerate(STATUSES):
        hours = totals.get(status, 0.0)
        grand += hours
        row_y  = _row_y(i)
        draw.text(
            (GRID_RIGHT + 6, row_y + ROW_H // 2 - 7),
            f"{hours:.2f}",
            font=f_total,
            fill=BLACK,
        )

    # Grand total (should equal 24)
    bottom_y = _row_y(NUM_ROWS)
    draw.line([(GRID_RIGHT, bottom_y + 4), (W - MARGIN_RIGHT, bottom_y + 4)], fill=BLACK, width=1)
    draw.text((GRID_RIGHT + 6, bottom_y + 6), f"{grand:.2f}", font=f_total, fill=BLACK)
    draw.text((GRID_RIGHT + 6, bottom_y + 22), "= 24", font=_load_font(10), fill=GRAY)


def _draw_remarks(draw: ImageDraw.Draw, segments: List[dict]) -> None:
    """Draw the Remarks section with location/duty-status change entries."""
    f_label  = _load_font(13, bold=True)
    f_normal = _load_font(12)
    f_small  = _load_font(10)

    draw.text((MARGIN_LEFT, REMARKS_TOP), "Remarks", font=f_label, fill=BLACK)
    draw.line(
        [(MARGIN_LEFT, REMARKS_TOP + 18), (W - MARGIN_RIGHT, REMARKS_TOP + 18)],
        fill=BLACK, width=1,
    )

    # Build remark lines from segments that have a location + status change
    lines: List[str] = []
    prev_status = None
    for seg in segments:
        status   = seg.get("status", "")
        location = seg.get("location", "").strip()
        time_str = seg.get("start_time", "")
        desc     = seg.get("description", "")

        if status != prev_status and location:
            status_label = {
                "off_duty":            "Off Duty",
                "sleeper_berth":       "Sleeper Berth",
                "driving":             "Driving",
                "on_duty_not_driving": "On Duty (Not Driving)",
            }.get(status, status)
            lines.append(f"{time_str}  {status_label} — {location}  [{desc}]")
            prev_status = status

    # Render up to 8 remark lines
    x_cur = MARGIN_LEFT
    y_cur = REMARKS_TOP + 26
    col_w = (W - MARGIN_RIGHT - MARGIN_LEFT) // 2

    for i, line in enumerate(lines[:8]):
        col = i % 2
        row = i // 2
        x   = MARGIN_LEFT + col * col_w
        y   = y_cur + row * 16
        draw.text((x, y), line[:90], font=f_normal, fill=BLACK)

    # Remarks section border
    draw.rectangle(
        [MARGIN_LEFT, REMARKS_TOP + 18,
         W - MARGIN_RIGHT, REMARKS_TOP + REMARKS_H],
        outline=BLACK, width=1,
    )

    # Shipping doc label
    draw.text(
        (MARGIN_LEFT, REMARKS_TOP + REMARKS_H - 20),
        "Shipping Documents / Pro or Manifest No.:",
        font=f_small, fill=GRAY,
    )


def _draw_recap(draw: ImageDraw.Draw, totals: dict, day: int, summary: dict) -> None:
    """Draw the 70 hr/8-day recap table at the bottom."""
    f_label  = _load_font(11, bold=True)
    f_normal = _load_font(10)
    f_small  = _load_font(9)

    y = RECAP_TOP
    draw.line([(MARGIN_LEFT, y), (W - MARGIN_RIGHT, y)], fill=BLACK, width=1)
    draw.text((MARGIN_LEFT, y + 4), "Recap: Complete at end of day", font=f_label, fill=BLACK)

    # 70 hr / 8 day table header
    col_starts = [220, 340, 460, 580]
    draw.text((220, y + 4), "70 Hour / 8 Day", font=f_label, fill=BLACK)
    draw.text((220, y + 18), "A.", font=f_normal, fill=BLACK)
    draw.text((340, y + 18), "B.", font=f_normal, fill=BLACK)
    draw.text((460, y + 18), "C.", font=f_normal, fill=BLACK)

    col_labels = [
        "A. Total hours on\nduty today.\nTotal lines 3 & 4",
        "B. Total hours\navailable tomorrow\n(70 hr. minus A*)",
        "C. Total hours on\nduty last 7 days\nincluding today",
    ]
    on_duty_today = round(
        totals.get("driving", 0) + totals.get("on_duty_not_driving", 0), 2
    )
    cycle_after      = summary.get("cycle_hours_after",     0) or 0
    cycle_remaining  = summary.get("cycle_hours_remaining", 0) or 0

    values = [on_duty_today, round(cycle_remaining, 2), round(cycle_after, 2)]

    for i, (lbl, val) in enumerate(zip(col_labels, values)):
        x = col_starts[i]
        for li, line in enumerate(lbl.split("\n")):
            draw.text((x, y + 32 + li * 11), line, font=f_small, fill=BLACK)
        draw.text((x, y + 72), str(val), font=f_label, fill=BLACK)

    draw.text(
        (700, y + 4),
        "*If you took 34 consecutive hours off duty you have 60/70 hours available",
        font=f_small,
        fill=BLACK,
    )


def _draw_legend(draw: ImageDraw.Draw) -> None:
    """Small color legend in the bottom-right corner."""
    f = _load_font(10)
    x, y = W - 300, RECAP_TOP + 4

    for status, label in [
        ("off_duty",            "Off Duty"),
        ("sleeper_berth",       "Sleeper Berth"),
        ("driving",             "Driving"),
        ("on_duty_not_driving", "On Duty (Not Driving)"),
    ]:
        color = STATUS_COLORS[status]
        draw.rectangle([x, y + 2, x + 14, y + 12], fill=color, outline=BLACK, width=1)
        draw.text((x + 18, y), label, font=f, fill=BLACK)
        y += 16


# ── Public API ────────────────────────────────────────────────────────────────

def generate_log_image(
    day:        int,
    segments:   List[dict],
    totals:     dict,
    summary:    dict,
    header:     Optional[dict] = None,
) -> bytes:
    """
    Render a single ELD daily log sheet as a PNG and return raw bytes.

    Args:
        day       : Day number (1-indexed).
        segments  : List of DailyLogSegment dicts with keys:
                    status, start_hour, end_hour, duration,
                    description, location, start_time, end_time.
        totals    : Dict with keys off_duty, sleeper_berth, driving,
                    on_duty_not_driving (hours, must sum to 24).
        summary   : Trip summary dict (for recap section).
        header    : Optional dict for header fields. Defaults to empty.

    Returns:
        PNG bytes.
    """
    header = header or {}

    img  = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)

    # Light background for the grid area
    draw.rectangle(
        [GRID_LEFT, GRID_TOP + TICK_HEADER_H,
         GRID_RIGHT, GRID_TOP + GRID_H],
        fill=(250, 250, 250),
    )

    _draw_header(draw, header)
    _draw_grid_skeleton(draw)
    _draw_duty_lines(draw, segments)
    _draw_totals(draw, totals)
    _draw_remarks(draw, segments)
    _draw_recap(draw, totals, day, summary)
    _draw_legend(draw)

    # Day label overlay
    f_day = _load_font(14, bold=True)
    draw.text(
        (GRID_LEFT + 4, GRID_TOP + TICK_HEADER_H + 2),
        f"Day {day}",
        font=f_day,
        fill=(100, 100, 100),
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()


def generate_trip_logs(trip_data: dict) -> List[dict]:
    """
    Generate PNG log images for every day in a trip.

    Args:
        trip_data : Full trip response dict (from TripSerializer or plan_trip_view).

    Returns:
        List of dicts, one per day:
            { "day": int, "image_bytes": bytes, "totals": dict }
    """
    daily_logs = trip_data.get("daily_logs", [])
    summary    = trip_data.get("summary", {})
    inputs     = trip_data.get("inputs", {})

    results = []
    for log in daily_logs:
        header = {
            "date":          f"Day {log['day']}",
            "from_location": inputs.get("current_location", ""),
            "to_location":   inputs.get("dropoff_location", ""),
            "carrier_name":  inputs.get("carrier_name", ""),
            "driver_name":   inputs.get("driver_name", ""),
            "total_miles":   summary.get("total_distance_miles", ""),
        }
        image_bytes = generate_log_image(
            day      = log["day"],
            segments = log["segments"],
            totals   = log["totals"],
            summary  = log.get("recap", {}),
            header   = header,
        )
        results.append({
            "day":         log["day"],
            "image_bytes": image_bytes,
            "totals":      log["totals"],
        })

    return results