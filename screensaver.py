# ABOUTME: Terminal screensaver for Claude Code community events.
# ABOUTME: Shimmering CLAUDE logo with swimming squid mascots. Customise via config.json.

import datetime
import json
import math
import os
import random
import select
import sys
import termios
import time
import tty

# ---------------------------------------------------------------------------
# ANSI rendering helpers (replaces curses — no inter-line gap artifacts)
# ---------------------------------------------------------------------------

A_BOLD = 0x10000
A_DIM = 0x20000


def color(n):
    """Encode a 256-color index for combining with style flags."""
    return max(1, min(n, 255))


WARM = [173, 179, 180, 186, 187, 216, 217, 223, 224, 230, 209, 215, 174, 138, 144]


class Screen:
    """Thin wrapper that buffers ANSI escape output for flicker-free rendering."""

    def __init__(self):
        self.buf = []
        self._update_size()

    def _update_size(self):
        sz = os.get_terminal_size()
        self.w = sz.columns
        self.h = sz.lines

    def getmaxyx(self):
        self._update_size()
        return (self.h, self.w)

    def erase(self):
        self.buf = ['\033[H\033[2J']

    def flush(self):
        sys.stdout.write(''.join(self.buf))
        sys.stdout.flush()
        self.buf = []


def safe_addstr(scr, y, x, s, attr=0):
    """Position cursor and write styled text, clipping to screen bounds."""
    if y < 0 or y >= scr.h or x >= scr.w:
        return
    s = s[:max(0, scr.w - x)]
    if not s:
        return
    col = attr & 0xFFFF
    bold = attr & A_BOLD
    dim = attr & A_DIM
    style = '1' if bold else ('2' if dim else '0')
    # ANSI cursor positioning is 1-based
    scr.buf.append(f'\033[{y+1};{x+1}H\033[{style};38;5;{col}m{s}\033[0m')


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _key_pressed():
    """Check if a key has been pressed (non-blocking)."""
    return select.select([sys.stdin], [], [], 0)[0]


def _read_key():
    """Read a single character from stdin."""
    return sys.stdin.read(1)

# ---------------------------------------------------------------------------
# The one and only canvas: shimmering logo
# ---------------------------------------------------------------------------

TITLE_LINES = [
    "        ▄▄▄▄▄▄▄▄      ▄▄▄▄                      ▄▄▄▄          ▄▄▄▄        ▄▄▄▄    ▄▄▄▄▄▄▄▄▄▄          ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄",
    "        ▄▄▄▄▄▄▄▄      ▄▄▄▄                      ▄▄▄▄          ▄▄▄▄        ▄▄▄▄    ▄▄▄▄▄▄▄▄▄▄          ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄",
    "    ████▀▀▀▀▀▀▀▀██    ████                    ████████        ████        ████    ████▀▀▀▀▀▀████      ████▀▀▀▀▀▀▀▀▀▀▀▀",
    "    ████▀▀▀▀▀▀▀▀██    ████                    ████████        ████        ████    ████▀▀▀▀▀▀████      ████▀▀▀▀▀▀▀▀▀▀▀▀",
    "  ████▀▀              ████                    ████████        ████        ████    ████        ████    ████              ",
    "  ████▀▀              ████                    ████████        ████        ████    ████        ████    ████              ",
    "  ████                ████                  ████    ████      ████        ████    ████        ████    ██████████████  ",
    "  ████                ████                  ████    ████      ████        ████    ████        ████    ██████████████  ",
    "  ████▄▄              ████                  ████████████      ████        ████    ████        ████    ████              ",
    "  ████▄▄              ████                  ████████████      ████        ████    ████        ████    ████              ",
    "    ████▄▄▄▄▄▄▄▄██    ████▄▄▄▄▄▄▄▄▄▄▄▄    ▄▄████    ████▄▄    ▀▀████▄▄▄▄████▀▀    ████▄▄▄▄▄▄████      ████▄▄▄▄▄▄▄▄▄▄▄▄",
    "    ████▄▄▄▄▄▄▄▄██    ████▄▄▄▄▄▄▄▄▄▄▄▄    ▄▄████    ████▄▄    ▀▀████▄▄▄▄████▀▀    ████▄▄▄▄▄▄████      ████▄▄▄▄▄▄▄▄▄▄▄▄",
    "        ▀▀▀▀▀▀▀▀      ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀    ▀▀▀▀        ▀▀▀▀        ▀▀▀▀▀▀▀▀        ▀▀▀▀▀▀▀▀▀▀          ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀",
    "        ▀▀▀▀▀▀▀▀      ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀    ▀▀▀▀        ▀▀▀▀        ▀▀▀▀▀▀▀▀        ▀▀▀▀▀▀▀▀▀▀          ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀",
]

# ---------------------------------------------------------------------------
# Config loading — customise your event via config.json
# ---------------------------------------------------------------------------

def _load_config():
    """Load config.json from the same directory as this script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return {}

_CFG = _load_config()

# Build display strings from config (with sensible defaults)
_subtitle_word = _CFG.get("subtitle", "CODE CURIOUS")
SUBTITLE = "   ".join(_subtitle_word)

VERBS = _CFG.get("verbs", [
    "Reticulating splines...",
    "Compiling thoughts...",
    "Grepping for meaning...",
    "Rebasing reality...",
    "Initializing curiosity...",
    "Parsing the void...",
    "Optimizing vibes...",
    "Aligning tokens...",
    "Hydrating the cache...",
    "Unwinding the stack...",
    "Resolving dependencies...",
    "Defragmenting ideas...",
    "Warming up the neurons...",
    "Indexing possibilities...",
    "Negotiating with the compiler...",
    "Untangling spaghetti...",
    "Calibrating enthusiasm...",
    "Consulting the oracle...",
    "Deploying butterflies...",
    "Refactoring the universe...",
])

_agenda_items = _CFG.get("agenda", [])
AGENDA = [f"{item['time']}   {item['label']}" for item in _agenda_items]

_event_date = _CFG.get("event_date", "")
_venue = _CFG.get("venue", "")
DATE_LINE = f"{_event_date}  ·  {_venue}" if _event_date and _venue else ""

_wifi = _CFG.get("wifi", "")
WIFI_LINE = f"WiFi:  {_wifi}" if _wifi else ""

GO_HOME_MESSAGES = _CFG.get("go_home_messages", [
    "Time to go home!",
    "Your sofa misses you",
    "The pub is calling...",
    "Last one out gets the light",
    "git commit -m 'gone home'",
])

# Urgency ramp: derived from the last agenda item's time
_urgency_mins_before = _CFG.get("urgency_start_minutes_before_end", 40)
if _agenda_items:
    _end_parts = _agenda_items[-1]["time"].split(":")
    _end_h, _end_m = int(_end_parts[0]), int(_end_parts[1])
    _end_total = _end_h * 60 + _end_m
    _start_total = _end_total - _urgency_mins_before
    URGENCY_START = datetime.time(_start_total // 60, _start_total % 60)
    URGENCY_END = datetime.time(_end_h, _end_m)
    URGENCY_MINUTES = float(_urgency_mins_before)
else:
    URGENCY_START = datetime.time(23, 59)
    URGENCY_END = datetime.time(23, 59)
    URGENCY_MINUTES = 1.0


def get_urgency():
    """Return 0.0–1.0+ based on how close to the end time we are."""
    now = datetime.datetime.now().time()
    start_mins = URGENCY_START.hour * 60 + URGENCY_START.minute
    now_mins = now.hour * 60 + now.minute + now.second / 60
    if now_mins < start_mins:
        return 0.0
    return (now_mins - start_mins) / URGENCY_MINUTES


def draw_logo(scr, t, verb_idx):
    """Draw the shimmering logo, subtitle, verbs, and date."""
    h, w = scr.getmaxyx()

    title_w = max(len(l) for l in TITLE_LINES)
    # Centre vertically (slightly above middle)
    start_y = max(1, h // 2 - len(TITLE_LINES) - 3)
    start_x = max(0, (w - title_w) // 2)

    # Block-letter title with shimmer
    for i, line in enumerate(TITLE_LINES):
        for j, ch in enumerate(line):
            if ch == ' ':
                continue
            shimmer = math.sin(j * 0.3 + t * 0.4 + (i // 2) * 0.5)
            ci_idx = int((shimmer + 1) / 2 * len(WARM)) % len(WARM)
            safe_addstr(scr, start_y + i, start_x + j, ch,
                        color(WARM[ci_idx]) | A_BOLD)

    # "C O D E   C U R I O U S" subtitle
    sub_y = start_y + len(TITLE_LINES) + 1
    sub_x = max(0, (w - len(SUBTITLE)) // 2)
    for j, ch in enumerate(SUBTITLE):
        shimmer = math.sin(j * 0.4 + t * 0.3)
        ci_idx = int((shimmer + 1) / 2 * len(WARM)) % len(WARM)
        safe_addstr(scr, sub_y, sub_x + j, ch,
                    color(WARM[ci_idx]) | A_BOLD)

    # Rotating spinner verb
    verb = VERBS[verb_idx]
    verb_y = sub_y + 2
    verb_x = max(0, (w - len(verb)) // 2)
    glow = int((math.sin(t * 0.5) + 1) / 2 * 3)
    glow_colors = [240, 245, 250, 255]
    safe_addstr(scr, verb_y, verb_x, verb, color(glow_colors[glow]))

    # Agenda block (centred, above bottom info) with go-home urgency
    urgency = get_urgency()
    agenda_start_y = h - 3 - len(AGENDA) - 1

    for i, line in enumerate(AGENDA):
        ax = max(0, (w - len(line)) // 2)
        if i < len(AGENDA) - 1:
            # Normal agenda items
            safe_addstr(scr, agenda_start_y + i, ax, line, color(252))
        else:
            # "Time to go home!" line — escalates with urgency
            if urgency >= 1.0:
                # Past 20:00: cycle through increasingly desperate messages
                msg_idx = min(int((urgency - 1.0) * 5), len(GO_HOME_MESSAGES) - 1)
                line = f"20:00   {GO_HOME_MESSAGES[msg_idx]}"
                ax = max(0, (w - len(line)) // 2)
            if urgency < 0.2:
                # Barely noticeable: normal color
                safe_addstr(scr, agenda_start_y + i, ax, line, color(252))
            elif urgency < 0.5:
                # Gentle pulse between white and warm orange
                pulse = (math.sin(t * 1.5) + 1) / 2
                c = 252 if pulse < 0.5 else 216
                safe_addstr(scr, agenda_start_y + i, ax, line, color(c) | A_BOLD)
            elif urgency < 0.8:
                # Stronger pulse, red tones
                pulse = (math.sin(t * 3) + 1) / 2
                c = 196 if pulse > 0.3 else 209
                safe_addstr(scr, agenda_start_y + i, ax, line, color(c) | A_BOLD)
            else:
                # Flashing red/white
                flash = int(t * 4) % 2
                c = 196 if flash else 255
                safe_addstr(scr, agenda_start_y + i, ax, line, color(c) | A_BOLD)

    # Date/venue and wifi at bottom (plain text, readable)
    date_y = h - 3
    date_x = max(0, (w - len(DATE_LINE)) // 2)
    safe_addstr(scr, date_y, date_x, DATE_LINE, color(245))
    wifi_y = h - 2
    wifi_x = max(0, (w - len(WIFI_LINE)) // 2)
    safe_addstr(scr, wifi_y, wifi_x, WIFI_LINE, color(252) | A_BOLD)

# ---------------------------------------------------------------------------
# Easter eggs — subtle overlays drawn ON TOP of the logo canvas
# ---------------------------------------------------------------------------

# The Claude Code mascot — exact characters from the real CLI.
# Eyes are formed by missing quadrants in ▛ and ▜.
SQUID_BODY = [
    " \u2590\u259b\u2588\u2588\u2588\u259c\u258c ",   #  ▐▛███▜▌  (padded to 9)
    "\u259d\u259c\u2588\u2588\u2588\u2588\u2588\u259b\u2598",  # ▝▜█████▛▘ (9)
]
# Two leg frames for subtle walk animation
SQUID_LEGS = [
    "  \u2598\u2598 \u259d\u259d  ",              #   ▘▘ ▝▝   (padded to 9)
    "  \u259d\u259d \u2598\u2598  ",              #   ▝▝ ▘▘   (swapped)
]
SQUID_W = max(len(l) for l in SQUID_BODY + SQUID_LEGS)
SQUID_COLOR = 216  # peach


class SquidSwim:
    """Claude Code squid swims across the screen with jellyfish propulsion."""

    def __init__(self, h, w):
        self.h = h
        self.w = w
        self.done = False
        self.frame = 0

        # Horizontal: drift steadily across
        self.going_right = random.choice([True, False])
        self.x = float(-SQUID_W if self.going_right else w)
        self.dx = random.uniform(0.2, 0.4) * (1 if self.going_right else -1)

        # Vertical: start in the gap between logo and agenda
        self.y = float(random.randint(h // 2 + 3, h - 8))
        self.vy = 0.0

        # Propulsion state
        self.zip_timer = 0       # frames until next zip
        self.zipping = False
        self.zip_frames_left = 0
        self._schedule_zip()

    def _schedule_zip(self):
        """Schedule the next upward zip."""
        self.zip_timer = random.randint(15, 35)

    def draw(self, scr, t):
        if self.done:
            return

        self.frame += 1

        # Propulsion: alternate between zipping up and drifting down
        if not self.zipping:
            self.zip_timer -= 1
            # Drift down gently
            self.vy = min(self.vy + 0.01, 0.15)
            if self.zip_timer <= 0:
                self.zipping = True
                self.zip_frames_left = random.randint(10, 18)
        else:
            # Zip upward — tentacles contract (fast leg animation)
            self.vy = -0.55
            self.zip_frames_left -= 1
            if self.zip_frames_left <= 0:
                self.zipping = False
                self.vy = -0.1
                self._schedule_zip()

        # Move
        self.x += self.dx
        self.y += self.vy
        # Keep squids between the logo/verb area and the agenda block
        self.y = max(self.h // 2 + 3, min(self.h - 8, self.y))

        # Off-screen exit
        if self.going_right and self.x > self.w + 2:
            self.done = True
            return
        if not self.going_right and self.x < -SQUID_W - 2:
            self.done = True
            return

        # Leg animation: faster when zipping (propulsion), slower when drifting
        leg_speed = 3 if self.zipping else 10
        leg_frame = SQUID_LEGS[(self.frame // leg_speed) % 2]
        lines = SQUID_BODY + [leg_frame]

        ix, iy = int(self.x), int(self.y)
        squid_attr = color(SQUID_COLOR) | A_BOLD
        for i, line in enumerate(lines):
            safe_addstr(scr, iy + i, ix, line, squid_attr)


class FloatingHeart:
    """A heart that pops out when two squids meet, then floats upward and fades."""

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.dy = -0.12
        self.dx = random.uniform(-0.1, 0.1)
        self.life = 40  # frames
        self.done = False

    def draw(self, scr, t):
        if self.done:
            return
        self.y += self.dy
        self.x += self.dx
        self.life -= 1
        if self.life <= 0:
            self.done = True
            return
        attr = A_BOLD if self.life > 20 else (0 if self.life > 10 else A_DIM)
        # Pink/red heart
        heart_color = 204 if self.life > 20 else 210
        safe_addstr(scr, int(self.y), int(self.x), "♥",
                    color(heart_color) | attr)


class FloatingParticle:
    """A single particle that drifts slowly upward and fades."""

    CHARS = ["·", ".", "·"]

    def __init__(self, h, w):
        self.x = random.randint(2, w - 3)
        self.y = float(h - 1)
        self.dx = random.uniform(-0.3, 0.3)
        self.speed = random.uniform(0.05, 0.15)
        self.char = random.choice(self.CHARS)
        self.ci = random.choice(WARM)
        self.done = False

    def draw(self, scr, t):
        if self.done:
            return
        self.y -= self.speed
        self.x += self.dx
        h, w = scr.getmaxyx()
        if self.y < 0:
            self.done = True
            return
        # Fade based on height (brighter near bottom)
        progress = 1.0 - (self.y / h)
        if progress > 0.7:
            attr = A_DIM
        elif progress > 0.3:
            attr = 0
        else:
            attr = A_BOLD
        safe_addstr(scr, int(self.y), int(self.x), self.char,
                    color(self.ci) | attr)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        # Alternate screen buffer + hide cursor + hide scrollbar
        sys.stdout.write('\033[?1049h\033[?25l\033[?30l')
        sys.stdout.flush()

        scr = Screen()
        verb_idx = 0
        last_verb_switch = time.monotonic()
        eggs = []  # active easter egg objects

        # Spawn squid immediately so we can check it
        h, w = scr.getmaxyx()
        eggs.append(SquidSwim(h, w))
        next_egg_time = time.monotonic() + random.uniform(15, 35)

        while True:
            t = time.monotonic()

            # Rotate verbs every ~8s
            if t - last_verb_switch > 8:
                verb_idx = (verb_idx + 1) % len(VERBS)
                last_verb_switch = t

            # Maybe spawn an easter egg
            if t > next_egg_time:
                h, w = scr.getmaxyx()
                roll = random.random()
                if roll < 0.65:
                    eggs.append(SquidSwim(h, w))
                else:
                    for _ in range(random.randint(1, 3)):
                        eggs.append(FloatingParticle(h, w))
                next_egg_time = t + random.uniform(10, 25)

            # --- Draw frame ---
            scr.erase()
            draw_logo(scr, t, verb_idx)

            # Draw active eggs on top
            for egg in eggs:
                egg.draw(scr, t)

            # Check for squid collisions → spawn hearts
            squids = [e for e in eggs if isinstance(e, SquidSwim) and not e.done]
            for i_s in range(len(squids)):
                for j_s in range(i_s + 1, len(squids)):
                    a, b = squids[i_s], squids[j_s]
                    if abs(a.x - b.x) < SQUID_W and abs(a.y - b.y) < 3:
                        # Only spawn once per close encounter (use frame parity)
                        if a.frame % 20 == 0:
                            mid_x = int((a.x + b.x) / 2) + SQUID_W // 2
                            mid_y = int(min(a.y, b.y)) - 1
                            eggs.append(FloatingHeart(mid_x, mid_y))

            eggs = [e for e in eggs if not e.done]

            scr.flush()
            time.sleep(0.08)

            # Check for quit
            if _key_pressed():
                ch = _read_key()
                if ch == 'q':
                    return

    finally:
        # Restore terminal: leave alternate screen, show cursor, reset attrs
        sys.stdout.write('\033[?1049l\033[?25h\033[0m')
        sys.stdout.flush()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
