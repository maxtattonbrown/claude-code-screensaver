# ABOUTME: Terminal screensaver for Claude Code community events.
# ABOUTME: Shimmering CLAUDE logo with scuttling CCC crab mascots. Customise via config.json.

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
        # Overwrite every line with spaces instead of \033[2J which flashes
        self._update_size()
        blank = ' ' * self.w
        self.buf = ['\033[H\033[0m']
        for row in range(self.h):
            self.buf.append(f'\033[{row+1};1H{blank}')

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
    "    ▄▄▄▄   ▄▄           ▄▄     ▄▄    ▄▄  ▄▄▄▄▄     ▄▄▄▄▄▄▄▄ ",
    "  ██▀▀▀▀█  ██          ████    ██    ██  ██▀▀▀██   ██▀▀▀▀▀▀ ",
    " ██▀       ██          ████    ██    ██  ██    ██  ██       ",
    " ██        ██         ██  ██   ██    ██  ██    ██  ███████  ",
    " ██▄       ██         ██████   ██    ██  ██    ██  ██       ",
    "  ██▄▄▄▄█  ██▄▄▄▄▄▄  ▄██  ██▄  ▀██▄▄██▀  ██▄▄▄██   ██▄▄▄▄▄▄ ",
    "    ▀▀▀▀   ▀▀▀▀▀▀▀▀  ▀▀    ▀▀    ▀▀▀▀    ▀▀▀▀▀     ▀▀▀▀▀▀▀▀",
]

# ---------------------------------------------------------------------------
# Config loading — customise your event via config.json
# ---------------------------------------------------------------------------

def _load_config():
    """Load config.json from the same directory as this script, or a path given as argv[1]."""
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
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
            shimmer = math.sin(j * 0.3 + t * 0.4 + i * 0.5)
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
# Easter eggs — overlays drawn ON TOP of the logo canvas
# ---------------------------------------------------------------------------

# The CCC crab — uses the Clawd (Claude Code mascot) sprite.
# Eyes are formed by missing quadrants in ▛ and ▜.
CRAB_BODY = [
    " \u2590\u259b\u2588\u2588\u2588\u259c\u258c ",   #  ▐▛███▜▌  (padded to 9)
    "\u259d\u259c\u2588\u2588\u2588\u2588\u2588\u259b\u2598",  # ▝▜█████▛▘ (9)
]
# Two leg frames for scuttle animation
CRAB_LEGS = [
    "  \u2598\u2598 \u259d\u259d  ",              #   ▘▘ ▝▝   (padded to 9)
    "  \u259d\u259d \u2598\u2598  ",              #   ▝▝ ▘▘   (swapped)
]
CRAB_W = max(len(l) for l in CRAB_BODY + CRAB_LEGS)
CRAB_COLOR = 208  # orange (matching the CCC brand)
MAX_CRABS = 5     # max small crabs on screen at once

# Accessories some crabs carry (char, color) — drawn above the crab
ACCESSORY_POOL = [
    None, None, None,           # ~43% no accessory
    ("\u2726", 226),             # ✦ lightbulb — yellow
    ("\u2726", 226),             # ✦ lightbulb (higher weight)
    ("\u25ce", 252),             # ◎ magnifying glass — white
    ("?", 255),                  # ? question mark — bright white
]


class CrabScuttle:
    """CCC crab scuttles sideways, optionally carrying an accessory icon."""

    def __init__(self, h, w):
        self.h = h
        self.w = w
        self.done = False
        self.frame = 0
        self.mode = 'scuttle'  # 'scuttle', 'chat', 'flee'

        # Random accessory (lightbulb, magnifying glass, ?, or none)
        self.accessory = random.choice(ACCESSORY_POOL)

        # Chat state
        self.chat_timer = 0
        self.chat_partner = None
        self.chat_cooldown = 0  # frames of immunity after a chat ends

        # Crabs primarily move sideways
        self.going_right = random.choice([True, False])
        self.x = float(-CRAB_W if self.going_right else w)
        self.dx = random.uniform(0.25, 0.5) * (1 if self.going_right else -1)

        # Vertical: pick a row in the gap between logo/verb area and agenda
        self.y = float(random.randint(h // 2 + 3, h - 8))
        self.vy = 0.0

        # Scuttle rhythm: bursts of fast movement with pauses
        self.pause_timer = 0
        self.paused = False
        self._schedule_pause()

    def _schedule_pause(self):
        """Schedule the next pause in scuttling."""
        self.pause_timer = random.randint(20, 50)

    def _resume_scuttle(self):
        """Return to scuttling after a chat ends."""
        self.mode = 'scuttle'
        self.chat_partner = None
        self.chat_cooldown = 40
        self._schedule_pause()

    def draw(self, scr, t):
        if self.done:
            return

        self.frame += 1

        if self.mode == 'flee':
            # Panic! Run toward the nearest edge at high speed
            self.x += self.dx
            self.y -= 0.3
            if self.x < -CRAB_W - 2 or self.x > self.w + 2:
                self.done = True
                return

        elif self.mode == 'chat':
            # Hold position — chatting with a friend
            self.chat_timer -= 1
            if self.chat_timer <= 0:
                # Chat over — swap accessories with partner and resume
                if self.chat_partner and not self.chat_partner.done:
                    self.accessory, self.chat_partner.accessory = (
                        self.chat_partner.accessory, self.accessory)
                    self.chat_partner._resume_scuttle()
                self._resume_scuttle()

        else:  # 'scuttle'
            if self.chat_cooldown > 0:
                self.chat_cooldown -= 1
            if not self.paused:
                self.pause_timer -= 1
                if self.pause_timer <= 0:
                    self.paused = True
                    self.pause_timer = random.randint(8, 20)
            else:
                self.pause_timer -= 1
                if self.pause_timer <= 0:
                    self.paused = False
                    self._schedule_pause()
                    self.vy = random.uniform(-0.1, 0.1)

            if not self.paused:
                self.x += self.dx
            self.y += self.vy
            self.vy *= 0.95
            self.y = max(self.h // 2 + 3, min(self.h - 8, self.y))

            # Off-screen exit
            if self.x > self.w + 2 or self.x < -CRAB_W - 2:
                self.done = True
                return

        # Leg animation — still when chatting, frantic when fleeing, rhythmic otherwise
        if self.mode == 'chat':
            leg_idx = 0
        else:
            divisor = 2 if self.mode == 'flee' else (5 if not self.paused else 8)
            leg_idx = (self.frame // divisor) % 2
        lines = CRAB_BODY + [CRAB_LEGS[leg_idx]]

        ix, iy = int(self.x), int(self.y)
        crab_attr = color(CRAB_COLOR) | A_BOLD
        for i, line in enumerate(lines):
            safe_addstr(scr, iy + i, ix, line, crab_attr)

        # Draw accessory above the crab (with slight bob)
        if self.accessory:
            acc_char, acc_color = self.accessory
            bob = math.sin(t * 2 + self.x) * 0.4
            acc_y = iy - 1 + int(bob)
            acc_x = ix + CRAB_W // 2
            safe_addstr(scr, acc_y, acc_x, acc_char, color(acc_color) | A_BOLD)

        # Draw chat bubbles when chatting
        if self.mode == 'chat':
            dots = "..." if (self.frame // 10) % 2 == 0 else " . "
            safe_addstr(scr, iy - 1, ix + CRAB_W // 2 - 1, dots, color(252))


# Big crab head for peeking up from screen bottom — no arms/legs needed.
# Solid block with eye sockets, 50 chars wide, 8 rows tall.
BIG_CRAB_OPEN = [
    '██████████████████████████████████████████████████',
    '██████████████████████████████████████████████████',
    '████████████      ██████████████      ████████████',
    '████████████      ██████████████      ████████████',
    '████████████      ██████████████      ████████████',
    '██████████████████████████████████████████████████',
    '██████████████████████████████████████████████████',
    '██████████████████████████████████████████████████',
]
BIG_CRAB_W = max(len(l) for l in BIG_CRAB_OPEN)
BIG_CRAB_H = len(BIG_CRAB_OPEN)
BIG_CRAB_BLINK = ['██████████████████████████████████████████████████'] * BIG_CRAB_H


class CrabPeek:
    """A big crab peeks up from the bottom of the screen, blinks, then sinks back."""

    def __init__(self, h, w):
        self.h = h
        self.w = w
        self.done = False
        self.frame = 0
        self.x = (w - BIG_CRAB_W) // 2 + random.randint(-10, 10)
        self.y = float(h)
        # Peek target: show top ~6 rows (eyes visible)
        self.target_y = float(h - BIG_CRAB_H + 2)
        self.phase = 'rising'  # 'rising', 'peeking', 'sinking'
        self.peek_timer = 0
        self.blink_until = 0
        self.next_blink = 0

    def draw(self, scr, t):
        if self.done:
            return

        self.frame += 1

        if self.phase == 'rising':
            self.y -= 0.15
            if self.y <= self.target_y:
                self.y = self.target_y
                self.phase = 'peeking'
                self.peek_timer = self.frame + 100
                self.next_blink = self.frame + random.randint(15, 30)

        elif self.phase == 'peeking':
            if self.frame > self.peek_timer:
                self.phase = 'sinking'
            if self.frame >= self.next_blink and self.blink_until <= self.frame:
                self.blink_until = self.frame + random.randint(3, 6)
                self.next_blink = self.frame + random.randint(15, 35)

        elif self.phase == 'sinking':
            self.y += 0.15
            if self.y > self.h:
                self.done = True
                return

        blinking = self.phase == 'peeking' and self.frame < self.blink_until
        sprite = BIG_CRAB_BLINK if blinking else BIG_CRAB_OPEN

        ix, iy = int(self.x), int(self.y)
        crab_attr = color(CRAB_COLOR) | A_BOLD
        for i, line in enumerate(sprite):
            safe_addstr(scr, iy + i, ix, line, crab_attr)


class FloatingParticle:
    """A single particle that drifts slowly upward and fades."""

    CHARS = ["\u00b7", ".", "\u00b7"]

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
        sys.stdout.write('\033[?1049h\033[?25l\033[?30l')
        sys.stdout.flush()

        scr = Screen()
        verb_idx = 0
        last_verb_switch = time.monotonic()
        eggs = []

        # Spawn a crab immediately
        h, w = scr.getmaxyx()
        eggs.append(CrabScuttle(h, w))
        next_egg_time = time.monotonic() + random.uniform(5, 12)

        # Peek event: rare big crab rising from the bottom
        next_peek_time = time.monotonic() + random.uniform(10, 15)

        while True:
            t = time.monotonic()

            # Rotate verbs every ~8s
            if t - last_verb_switch > 8:
                verb_idx = (verb_idx + 1) % len(VERBS)
                last_verb_switch = t

            # Spawn crabs/particles (respect max crab limit)
            if t > next_egg_time:
                h, w = scr.getmaxyx()
                active_crabs = sum(1 for e in eggs
                                   if isinstance(e, CrabScuttle) and not e.done)
                if random.random() < 0.80 and active_crabs < MAX_CRABS:
                    eggs.append(CrabScuttle(h, w))
                else:
                    for _ in range(random.randint(1, 3)):
                        eggs.append(FloatingParticle(h, w))
                next_egg_time = t + random.uniform(8, 18)

            # Maybe spawn a peek crab
            if t > next_peek_time:
                h, w = scr.getmaxyx()
                has_peek = any(isinstance(e, CrabPeek) and not e.done
                               for e in eggs)
                if not has_peek:
                    eggs.append(CrabPeek(h, w))
                    # Scatter all small crabs — they flee the big one!
                    center_x = w / 2.0
                    for e in eggs:
                        if isinstance(e, CrabScuttle) and not e.done:
                            e.mode = 'flee'
                            e.chat_partner = None
                            if e.x < center_x:
                                e.dx = -random.uniform(0.8, 1.5)
                            else:
                                e.dx = random.uniform(0.8, 1.5)
                next_peek_time = t + random.uniform(60, 120)

            # --- Draw frame ---
            scr.erase()
            draw_logo(scr, t, verb_idx)

            for egg in eggs:
                egg.draw(scr, t)

            # Crab collisions → start a chat (only if both scuttling and off cooldown)
            crabs = [e for e in eggs
                     if isinstance(e, CrabScuttle) and not e.done
                     and e.mode == 'scuttle' and e.chat_cooldown <= 0]
            for i_s in range(len(crabs)):
                a = crabs[i_s]
                if a.mode != 'scuttle':
                    continue  # already paired in an earlier iteration
                for j_s in range(i_s + 1, len(crabs)):
                    b = crabs[j_s]
                    if (b.mode == 'scuttle'
                            and abs(a.x - b.x) < CRAB_W
                            and abs(a.y - b.y) < 3):
                        chat_len = random.randint(30, 60)
                        a.mode = b.mode = 'chat'
                        a.chat_timer = b.chat_timer = chat_len
                        a.chat_partner = b
                        b.chat_partner = a
                        break  # a is now chatting, move to next crab

            eggs = [e for e in eggs if not e.done]

            scr.flush()
            time.sleep(0.08)

            if _key_pressed():
                ch = _read_key()
                if ch == 'q':
                    return

    finally:
        sys.stdout.write('\033[?1049l\033[?25h\033[0m')
        sys.stdout.flush()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
