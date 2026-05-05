"""
ELD Log Sheet Generator — matches the FMCSA Driver's Daily Log paper format.

Canvas: 1100 × 1110 px (2.144× scale of the 513×518 original scan)
Duty lines: solid coloured lines (one per row) — same concept as paper but
            colour-coded for digital readability.
"""

from __future__ import annotations

import io
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

# ──────────────────────────────────────────────────────────────────────────────
# Canvas & scale
# ──────────────────────────────────────────────────────────────────────────────
ORIG_W, ORIG_H = 513, 518
SCALE          = 2.144          # keeps exact proportions of the scanned form
W = int(ORIG_W * SCALE)         # 1100
H = int(ORIG_H * SCALE) + 10   # 1121

def _s(px: float) -> int:
    """Scale an original-pixel value to canvas pixels."""
    return int(px * SCALE)


# ──────────────────────────────────────────────────────────────────────────────
# Colours
# ──────────────────────────────────────────────────────────────────────────────
WHITE  = (255, 255, 255)
BLACK  = (  0,   0,   0)
LGRAY  = (200, 200, 200)
DGRAY  = (100, 100, 100)
BGRAY  = (245, 245, 245)

STATUS_COLORS = {
    "off_duty":            ( 70, 130, 180),   # steel-blue
    "sleeper_berth":       ( 60, 160,  80),   # green
    "driving":             (210,  50,  40),   # red
    "on_duty_not_driving": (220, 150,  20),   # amber
}
STATUS_LABELS = {
    "off_duty":            "Off Duty",
    "sleeper_berth":       "Sleeper Berth",
    "driving":             "Driving",
    "on_duty_not_driving": "On Duty (Not Driving)",
}

# ──────────────────────────────────────────────────────────────────────────────
# Layout — all values derived from original scan measurements
# ──────────────────────────────────────────────────────────────────────────────

# Header section rows (original y values → scaled)
HDR_LINE1_Y   = _s(  0)   # top of title
HDR_SEP1_Y    = _s( 47)   # line below title / date row
HDR_SEP2_Y    = _s( 79)   # line below From/To row
HDR_SEP3_Y    = _s( 99)   # separator: mileage | carrier name
HDR_SEP4_Y    = _s(120)   # separator: truck numbers | main office
HDR_BOTTOM_Y  = _s(153)   # bottom of header / top of grid tick area

# Grid measurements
TICK_TOP_Y    = _s(154)   # top of tick-mark header band
TICK_BOT_Y    = _s(182)   # bottom of tick area / top of row 1

ROW_TOPS = [_s(y) for y in [182, 201, 218, 235]]   # top of each duty row
ROW_BOT_Y = _s(253)                                  # bottom of last row

# Column boundaries
LBL_LEFT      = _s(  0)   # left edge (includes row number label)
GRID_LEFT     = _s( 64)   # where the 24-hour grid starts
GRID_RIGHT    = _s(492)   # right edge of grid
TOTAL_RIGHT   = _s(513)   # right edge of Total Hours column
GRID_W        = GRID_RIGHT - GRID_LEFT

# Derived
ROW_H         = ROW_TOPS[1] - ROW_TOPS[0]   # height of one duty row

# Remarks & recap (original y → scaled)
RMK_TOP_Y     = _s(253) + 4
RMK_BOT_Y     = _s(418) - 4
RECAP_TOP_Y   = _s(418)
RECAP_BOT_Y   = _s(515)

# Per-hour pixel width
HOUR_PX       = GRID_W / 24.0

STATUSES = [
    ("off_duty",            "1. Off Duty"),
    ("sleeper_berth",       "2. Sleeper\n   Berth"),
    ("driving",             "3. Driving"),
    ("on_duty_not_driving", "4. On Duty\n   (Not Driving)"),
]


# ──────────────────────────────────────────────────────────────────────────────
# Font helpers
# ──────────────────────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    paths = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    )
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


# ──────────────────────────────────────────────────────────────────────────────
# Coordinate helpers
# ──────────────────────────────────────────────────────────────────────────────

def _x(hour: float) -> int:
    return int(GRID_LEFT + hour * HOUR_PX)


def _hline(draw, y, x0=None, x1=None, color=BLACK, width=1):
    draw.line([(x0 or LBL_LEFT, y), (x1 or TOTAL_RIGHT, y)], fill=color, width=width)


def _vline(draw, x, y0, y1, color=BLACK, width=1):
    draw.line([(x, y0), (x, y1)], fill=color, width=width)


def _text(draw, xy, txt, font, fill=BLACK, anchor="lt"):
    draw.text(xy, txt, font=font, fill=fill, anchor=anchor)


# ──────────────────────────────────────────────────────────────────────────────
# Section: Header
# ──────────────────────────────────────────────────────────────────────────────

def _draw_header(draw: ImageDraw.Draw, hdr: dict) -> None:
    ft  = _font(20, bold=True)   # title
    fb  = _font(14, bold=True)   # bold values
    fn  = _font(12)              # normal
    fs  = _font(10)              # small / label
    fxs = _font( 9)              # extra-small

    # ── Row 1: title | date | original note ──────────────────────────────────
    y = HDR_LINE1_Y + 4
    _text(draw, (_s(2), y),  "Drivers Daily Log", ft)
    _text(draw, (_s(2), y + _s(14)), "(24 hours)", fxs, fill=DGRAY)

    # Date slot  (month) / (day) / (year)
    date_val = hdr.get("date", "")
    _text(draw, (_s(100), y + 4), date_val, fb)
    for lbl, lx in [("(month)", 100), ("(day)", 145), ("(year)", 185)]:
        _text(draw, (_s(lx), y + _s(14)), lbl, fxs, fill=DGRAY)

    # Original / duplicate note  (right side)
    note_x = _s(260)
    _text(draw, (note_x, y),        "Original - File at home terminal.",         fxs)
    _text(draw, (note_x, y + _s(8)),"Duplicate - Driver retains in his/her possession for 8 days.", fxs)

    _hline(draw, HDR_SEP1_Y, width=1, color=LGRAY)

    # ── Row 2: From / To ─────────────────────────────────────────────────────
    y2 = HDR_SEP1_Y + 4
    _text(draw, (_s(2),  y2), "From:", fn, fill=DGRAY)
    _text(draw, (_s(2),  y2 + _s(10)), hdr.get("from_location", ""), fb)
    _text(draw, (_s(130), y2), "To:", fn, fill=DGRAY)
    _text(draw, (_s(145), y2 + _s(10)), hdr.get("to_location", ""), fb)

    _hline(draw, HDR_SEP2_Y, width=1, color=LGRAY)

    # ── Row 3: Mileage boxes | Carrier name ──────────────────────────────────
    y3 = HDR_SEP2_Y + 4
    # Two small boxes
    for bx, lbl, val in [
        (_s(2),  "Total Miles Driving Today", hdr.get("total_miles", "")),
        (_s(82), "Total Mileage Today",        hdr.get("total_mileage", "")),
    ]:
        bw, bh = _s(70), _s(18)
        draw.rectangle([bx, y3, bx + bw, y3 + bh], outline=BLACK, width=1)
        if val:
            _text(draw, (bx + 4, y3 + 3), str(val), fb)
        _text(draw, (bx, y3 + bh + 2), lbl, fxs, fill=DGRAY)

    # Carrier name (right half)
    rx = _s(260)
    _text(draw, (rx, y3),            hdr.get("carrier_name", ""), fb)
    _hline(draw, y3 + _s(18), x0=rx, color=BLACK, width=1)
    _text(draw, (rx, y3 + _s(20)),   "Name of Carrier or Carriers", fxs, fill=DGRAY)

    _hline(draw, HDR_SEP3_Y, x0=0, x1=_s(250), color=LGRAY, width=1)

    # ── Row 4: Truck numbers | Main office address ────────────────────────────
    y4 = HDR_SEP3_Y + 4
    _text(draw, (_s(2), y4),
          hdr.get("truck_numbers",
                  "Truck/Tractor and Trailer Numbers or License Plate(s)/State (show each unit)"),
          fxs, fill=DGRAY)

    rx2 = _s(260)
    _text(draw, (rx2, y4),          hdr.get("main_office", ""), fn)
    _hline(draw, y4 + _s(16), x0=rx2, color=BLACK, width=1)
    _text(draw, (rx2, y4 + _s(18)), "Main Office Address", fxs, fill=DGRAY)

    _hline(draw, HDR_SEP4_Y, x0=0, x1=_s(250), color=LGRAY, width=1)

    # ── Row 5: Signature | Home terminal ─────────────────────────────────────
    y5 = HDR_SEP4_Y + 4
    # Signature line
    _text(draw, (_s(2), y5), hdr.get("driver_name", ""), fn)
    _hline(draw, y5 + _s(16), x0=_s(2), x1=_s(250), color=BLACK, width=1)
    _text(draw, (_s(2), y5 + _s(18)),
          "I certify that these entries are true and correct", fxs, fill=DGRAY)

    # Home terminal (right)
    _text(draw, (_s(260), y5),          hdr.get("home_terminal", ""), fn)
    _hline(draw, y5 + _s(16), x0=_s(260), color=BLACK, width=1)
    _text(draw, (_s(260), y5 + _s(18)), "Home Terminal Address", fxs, fill=DGRAY)

    # Co-driver (right side, same height as home terminal)
    _text(draw, (_s(260), y5 + _s(22)), hdr.get("co_driver", ""), fn)
    _hline(draw, y5 + _s(38), x0=_s(260), x1=TOTAL_RIGHT, color=LGRAY, width=1)
    _text(draw, (_s(260), y5 + _s(40)), "Name of Co-Driver", fxs, fill=DGRAY)

    # Bottom header border
    _hline(draw, HDR_BOTTOM_Y, color=BLACK, width=2)


# ──────────────────────────────────────────────────────────────────────────────
# Section: Grid skeleton
# ──────────────────────────────────────────────────────────────────────────────

def _draw_grid(draw: ImageDraw.Draw) -> None:
    fh  = _font(10, bold=True)   # hour numbers
    fs  = _font( 8)              # small labels (Mid-night, Noon)
    flbl = _font(11)             # row labels

    # ── Tick-mark header band ─────────────────────────────────────────────────
    # Background
    draw.rectangle([GRID_LEFT, TICK_TOP_Y, GRID_RIGHT, TICK_BOT_Y], fill=BGRAY)

    # Outer grid border (tick band + all rows)
    draw.rectangle([GRID_LEFT, TICK_TOP_Y, GRID_RIGHT, ROW_BOT_Y],
                   outline=BLACK, width=2)

    # Hour labels and major/minor ticks
    tick_mid  = (TICK_TOP_Y + TICK_BOT_Y) // 2   # midpoint of tick band
    label_y   = TICK_TOP_Y + 2
    major_h   = TICK_BOT_Y - TICK_TOP_Y           # full tick height
    minor_h   = major_h // 3                      # 15-min tick height
    half_h    = major_h // 2                      # 30-min tick height

    for h in range(25):
        x = _x(h)

        # Major tick (full height at each hour)
        _vline(draw, x, TICK_TOP_Y, TICK_BOT_Y, width=1)

        # Label
        if h == 0:
            _text(draw, (x + 2, label_y),          "Mid-",  fs)
            _text(draw, (x + 2, label_y + _s(7)),  "night", fs)
        elif h == 24:
            _text(draw, (x - _s(14), label_y),         "Mid-",  fs)
            _text(draw, (x - _s(14), label_y + _s(7)), "night", fs)
        elif h == 12:
            _text(draw, (x + 2, label_y + 2), "Noon", fs)
        else:
            _text(draw, (x + 2, label_y + 4), str(h), fh)

        # Minor ticks between this hour and next (15-min, 30-min)
        if h < 24:
            for frac, th in [(1, minor_h), (2, half_h), (3, minor_h)]:
                qx = int(GRID_LEFT + (h + frac / 4) * HOUR_PX)
                _vline(draw, qx, TICK_BOT_Y - th, TICK_BOT_Y, width=1)

    # ── Duty-status rows ──────────────────────────────────────────────────────
    for i, (_, lbl) in enumerate(STATUSES):
        ry = ROW_TOPS[i]

        # Row top border
        _hline(draw, ry, x0=LBL_LEFT, x1=GRID_RIGHT, width=1)

        # Row label (left of grid)
        for li, line in enumerate(lbl.split("\n")):
            _text(draw, (LBL_LEFT + 2, ry + 3 + li * _s(9)), line, flbl)

        # Light hour-guide lines inside row
        for h in range(1, 24):
            _vline(draw, _x(h), ry + 1, ry + ROW_H - 1, color=LGRAY, width=1)

    # Bottom border of last row
    _hline(draw, ROW_BOT_Y, x0=LBL_LEFT, x1=GRID_RIGHT, width=2)

    # ── Total Hours column ────────────────────────────────────────────────────
    # Header
    fth = _font(9)
    _text(draw, (GRID_RIGHT + 4, TICK_TOP_Y + 2), "Total", fth)
    _text(draw, (GRID_RIGHT + 4, TICK_TOP_Y + _s(10)), "Hours", fth)
    # Right border of total column
    _vline(draw, TOTAL_RIGHT - 2, TICK_TOP_Y, ROW_BOT_Y, width=1)


# ──────────────────────────────────────────────────────────────────────────────
# Section: Duty lines
# ──────────────────────────────────────────────────────────────────────────────

def _draw_duty_lines(draw: ImageDraw.Draw, segments: List[dict]) -> None:
    """
    Draw a single solid horizontal line in each row for each segment.
    Vertical connector lines are drawn at status transitions (like the paper form).
    Line thickness = ~40% of row height, centred vertically.
    """
    LINE_H = max(4, int(ROW_H * 0.40))

    sorted_segs = sorted(segments, key=lambda s: s.get("start_hour", 0))

    for seg in sorted_segs:
        status     = seg.get("status", "off_duty")
        start_hour = float(seg.get("start_hour", 0))
        end_hour   = float(seg.get("end_hour",   0))
        if end_hour <= start_hour:
            continue

        row_idx = next((i for i, (s, _) in enumerate(STATUSES) if s == status), 0)
        color   = STATUS_COLORS.get(status, LGRAY)
        ry      = ROW_TOPS[row_idx]
        cy      = ry + ROW_H // 2
        x1, x2  = _x(start_hour), _x(end_hour)

        # Horizontal line
        draw.rectangle(
            [x1, cy - LINE_H // 2, x2, cy + LINE_H // 2],
            fill=color,
        )
        # Vertical drop-line at start
        _vline(draw, x1, ry + 1, ry + ROW_H - 1, color=color, width=2)
        # Vertical drop-line at end
        _vline(draw, x2, ry + 1, ry + ROW_H - 1, color=color, width=2)


# ──────────────────────────────────────────────────────────────────────────────
# Section: Total hours (right column)
# ──────────────────────────────────────────────────────────────────────────────

def _draw_totals(draw: ImageDraw.Draw, totals: dict) -> None:
    ft = _font(11, bold=True)
    fs = _font( 9)
    grand = 0.0

    for i, (status, _) in enumerate(STATUSES):
        hours  = round(totals.get(status, 0.0), 2)
        grand += hours
        ry     = ROW_TOPS[i]
        _text(draw, (GRID_RIGHT + 5, ry + ROW_H // 2 - _s(5)),
              f"{hours:.2f}", ft)

    # Grand total
    _hline(draw, ROW_BOT_Y + 4, x0=GRID_RIGHT, x1=TOTAL_RIGHT, width=1)
    _text(draw, (GRID_RIGHT + 5, ROW_BOT_Y + 6),  f"{grand:.2f}", ft)
    _text(draw, (GRID_RIGHT + 5, ROW_BOT_Y + 20), "= 24",         fs, fill=DGRAY)


# ──────────────────────────────────────────────────────────────────────────────
# Section: Remarks
# ──────────────────────────────────────────────────────────────────────────────

def _draw_remarks(draw: ImageDraw.Draw, segments: List[dict]) -> None:
    fb = _font(12, bold=True)
    fn = _font(11)
    fs = _font( 9)

    y = RMK_TOP_Y

    # Section label
    _text(draw, (LBL_LEFT + 2, y), "Remarks", fb)
    _hline(draw, y + _s(14), width=1)

    # Section border box
    draw.rectangle(
        [LBL_LEFT, y + _s(14), TOTAL_RIGHT, RMK_BOT_Y],
        outline=BLACK, width=1,
    )

    # Build remark entries — one line per duty change with location/miles/activity
    entries = []
    prev_status = None
    for seg in sorted(segments, key=lambda s: s.get("start_hour", 0)):
        status   = seg.get("status", "")
        location = seg.get("location", "").strip()
        t        = seg.get("start_time", "")
        desc     = seg.get("description", "")
        miles    = seg.get("miles", 0)

        if status != prev_status:
            slbl = STATUS_LABELS.get(status, status)
            parts = [f"{t} {slbl}"]
            if location:
                parts.append(f"@ {location}")
            if miles and float(miles) > 0:
                parts.append(f"({float(miles):.0f} mi)")
            if desc:
                parts.append(f"- {desc}")
            entries.append(" ".join(parts))
            prev_status = status

    # Single-column layout inside remarks box
    line_h = _s(12)
    for i, entry in enumerate(entries[:12]):
        ex = LBL_LEFT + 4
        ey = y + _s(18) + i * line_h
        if ey + line_h < RMK_BOT_Y - _s(30):
            _text(draw, (ex, ey), entry[:110], fn)

    # Sub-labels inside remarks box
    sub_y = RMK_BOT_Y - _s(30)
    _hline(draw, sub_y, width=1, color=LGRAY)
    _text(draw, (LBL_LEFT + 2, sub_y + 3),
          "Shipping Documents:", fs, fill=DGRAY)
    _text(draw, (LBL_LEFT + _s(110), sub_y + 3),
          "DVL or Manifest No.:", fs, fill=DGRAY)
    _text(draw, (LBL_LEFT + _s(220), sub_y + 3),
          "Shipper & Commodity:", fs, fill=DGRAY)

    # Instruction lines
    inst_y = RMK_BOT_Y - _s(50)
    _text(draw,
          (W // 2, inst_y),
          "Enter name of place you reported and where released from work "
          "and when and where each change of duty occurred.",
          fs, fill=DGRAY, anchor="mt")
    _text(draw,
          (W // 2, inst_y + _s(10)),
          "Use time standard of home terminal.",
          fs, fill=DGRAY, anchor="mt")



# ──────────────────────────────────────────────────────────────────────────────
# Section: Recap (70-hr / 8-day table)
# ──────────────────────────────────────────────────────────────────────────────

def _draw_recap(draw: ImageDraw.Draw, totals: dict, summary: dict) -> None:
    fb  = _font(11, bold=True)
    fn  = _font(10)
    fs  = _font( 9)
    fxs = _font( 8)

    y = RECAP_TOP_Y + _s(4)
    _hline(draw, RECAP_TOP_Y, width=2)

    on_duty_today   = round(totals.get("driving", 0) + totals.get("on_duty_not_driving", 0), 2)
    cycle_after     = round(summary.get("cycle_hours_after",     0) or 0, 2)
    cycle_remaining = round(summary.get("cycle_hours_remaining", 0) or 0, 2)

    # Left label
    _text(draw, (LBL_LEFT + 2, y),         "Recap:", fb)
    _text(draw, (LBL_LEFT + 2, y + _s(11)),"Complete at", fn)
    _text(draw, (LBL_LEFT + 2, y + _s(21)),"end of day",  fn)

    # ── 70 Hour / 8 Day block ─────────────────────────────────────────────────
    col70_x = _s(80)
    _text(draw, (col70_x, y), "70 Hour / 8 Day", fb)

    drv_lbl = "On duty\nhours\ntoday.\nTotal lines\n3 & 4"
    _text(draw, (col70_x, y + _s(12)), "Drivers", fs)

    col_ax, col_bx, col_cx = col70_x + _s(40), col70_x + _s(90), col70_x + _s(140)

    # Column A
    for li, line in enumerate(["A. Total", "hours on", "duty last 7", "days incl.", "today"]):
        _text(draw, (col_ax, y + _s(12) + li * _s(9)), line, fxs)
    _text(draw, (col_ax, y + _s(60)), str(cycle_after), fb)

    # Column B
    for li, line in enumerate(["B. Total", "hours", "available", "tomorrow", "70 hr-A*"]):
        _text(draw, (col_bx, y + _s(12) + li * _s(9)), line, fxs)
    _text(draw, (col_bx, y + _s(60)), str(cycle_remaining), fb)

    # Column C
    for li, line in enumerate(["C. Total", "hours on", "duty last 8", "days incl.", "today"]):
        _text(draw, (col_cx, y + _s(12) + li * _s(9)), line, fxs)
    _text(draw, (col_cx, y + _s(60)), str(on_duty_today), fb)

    # ── 60 Hour / 7 Day block ─────────────────────────────────────────────────
    col60_x = _s(280)
    _text(draw, (col60_x, y), "60 Hour / 7 Day", fb)

    col_a2x, col_b2x, col_c2x = col60_x + _s(40), col60_x + _s(90), col60_x + _s(140)
    _text(draw, (col60_x, y + _s(12)), "Day Drivers", fs)
    for li, line in enumerate(["A. Total", "hours on", "duty last 7", "days incl.", "today"]):
        _text(draw, (col_a2x, y + _s(12) + li * _s(9)), line, fxs)
    for li, line in enumerate(["B. Total", "hours", "available", "tomorrow", "60 hr-A*"]):
        _text(draw, (col_b2x, y + _s(12) + li * _s(9)), line, fxs)
    for li, line in enumerate(["C. Total", "hours on", "duty last 7", "days incl.", "today"]):
        _text(draw, (col_c2x, y + _s(12) + li * _s(9)), line, fxs)

    # Note
    note_x = _s(460)
    for li, line in enumerate([
        "*If you took",
        "34 consecutive",
        "hours off duty",
        "you have 60/70",
        "hours available",
    ]):
        _text(draw, (note_x, y + li * _s(10)), line, fxs)

    # ── Legend ────────────────────────────────────────────────────────────────
    lx, ly = _s(390), y + _s(4)
    for status, lbl in [
        ("off_duty",            "Off Duty"),
        ("sleeper_berth",       "Sleeper Berth"),
        ("driving",             "Driving"),
        ("on_duty_not_driving", "On Duty (Not Driving)"),
    ]:
        draw.rectangle([lx, ly + 2, lx + _s(10), ly + _s(10)],
                       fill=STATUS_COLORS[status], outline=BLACK, width=1)
        _text(draw, (lx + _s(13), ly), lbl, fxs)
        ly += _s(14)

    _hline(draw, RECAP_BOT_Y, width=1)


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def generate_log_image(
    day:      int,
    segments: List[dict],
    totals:   dict,
    summary:  dict,
    header:   Optional[dict] = None,
) -> bytes:
    """
    Render a single Driver's Daily Log sheet as PNG bytes.

    Args:
        day      : 1-based day number.
        segments : List of DailyLogSegment dicts
                   (status, start_hour, end_hour, duration,
                    description, location, start_time, end_time).
        totals   : {off_duty, sleeper_berth, driving, on_duty_not_driving}
                   summing to 24.
        summary  : Trip summary dict (cycle hours etc.).
        header   : Optional header field overrides.
    Returns:
        Raw PNG bytes.
    """
    hdr = header or {}

    img  = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)

    _draw_header(draw, hdr)
    _draw_grid(draw)
    _draw_duty_lines(draw, segments)
    _draw_totals(draw, totals)
    _draw_remarks(draw, segments)
    _draw_recap(draw, totals, summary)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()


def generate_trip_logs(trip_data: dict) -> List[dict]:
    """
    Generate one PNG log sheet per day of a trip.

    Args:
        trip_data : Full trip response dict (TripSerializer output).
    Returns:
        List of {day, image_bytes, totals}.
    """
    from datetime import datetime, timedelta

    daily_logs = trip_data.get("daily_logs", [])
    summary    = trip_data.get("summary",    {})
    inputs     = trip_data.get("inputs",     {})

    # Determine trip start date from created_at or use today
    created_at = trip_data.get("created_at", "")
    try:
        base_date = datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        base_date = datetime.now().date()

    results = []
    for log in daily_logs:
        day_num = log["day"]
        log_date = base_date + timedelta(days=day_num - 1)
        date_str = log_date.strftime("%m / %d / %Y")

        # Daily miles from HOS calculator
        daily_miles = log.get("daily_miles_driven", 0.0)
        cumulative_miles = log.get("cumulative_total_miles", 0.0)

        # Build per-day recap for the generator
        recap = log.get("recap", {})

        hdr = {
            "date":           date_str,
            "from_location":  inputs.get("current_location", ""),
            "to_location":    inputs.get("dropoff_location", ""),
            "carrier_name":   inputs.get("carrier_name", ""),
            "driver_name":    inputs.get("driver_name", ""),
            "total_miles":    str(round(daily_miles, 1)),
            "total_mileage":  str(round(cumulative_miles, 1)),
        }
        image_bytes = generate_log_image(
            day=day_num, segments=log["segments"],
            totals=log["totals"], summary={**summary, **recap}, header=hdr,
        )
        results.append({
            "day":         day_num,
            "image_bytes": image_bytes,
            "totals":      log["totals"],
        })
    return results