# Claude Code Event Screensaver

Python terminal screensaver for CCC (Claude Code Curious) community events. Shimmering CLAUDE block-art logo + rotating status messages + event info + animated squid mascots swimming across the screen.

**Not the CCC website** — that lives at `~/Projects/ccc-website/` (Hugo, separate repo). This is the screen the projector shows while people arrive.

## Stack

- Python 3.8+
- stdlib only — no `pip install` step
- Unix terminal (uses `termios`/`tty`; no Windows)
- Dark terminal theme assumed

## Run

```bash
python screensaver.py
```

`q` quits.

## Configuration

`config.json` next to `screensaver.py` controls per-event content:

```json
{
  "event_date": "15 Mar 2026",
  "venue": "Your Venue",
  "wifi": "YourWifiNetwork",
  "subtitle": "CODE LONDON",
  "agenda": [
    {"time": "18:00", "label": "Doors open"}
  ]
}
```

The big block-art title always says **CLAUDE**. `subtitle` appears below it with auto-spacing — set to `"CODE LA"`, `"CODE LONDON"`, etc. Event-specific variants live alongside as `config-<event>.json` (`config-cutting-edge.json` is the current example for CCC Cutting Edge).

## Demo

`demo.tape` is a [VHS](https://github.com/charmbracelet/vhs) script that renders `demo-v2.gif` / `demo-v2.mp4`. Re-render after meaningful visual changes.

## Editing the visuals

The shimmer, squid animation, and block-art are all in `screensaver.py` — single file, intentionally. If you find yourself reaching for a second file, ask whether the change is worth the complexity for what is fundamentally a 30-minute-of-attention pre-event prop.

## Related

- CCC website: `~/Projects/ccc-website/` (Hugo)
- CCC community on Cast: `cast.claudecodecurious.com`
- CCC mascot is a waving crab — the squids in this screensaver are a separate Anthropic visual (the Claude Code mascot)
