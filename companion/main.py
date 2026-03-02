#!/usr/bin/env python3
"""
TurtleDink Companion
====================
Watches the WoW SavedVariables file for TurtleDink level-up events and
forwards them to a Discord channel via webhook.

Usage:
    python main.py

Requires:
    pip install -r requirements.txt
"""

import glob
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR     = Path(__file__).parent
CONFIG_FILE    = SCRIPT_DIR / "config.json"
PROCESSED_FILE = SCRIPT_DIR / ".processed_events.json"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "discord_webhook_url": "",
    "wow_path": "",
    "check_interval_seconds": 10,
    "message_template": "**{player}** just reached level **{level}**! ({race} {class})",
    "use_embed": True,
    "embed_color": 16766720,  # Gold: 0xFFD700
}

CANDIDATE_WOW_PATHS = [
    r"C:\Turtle WoW",
    r"C:\TurtleWoW",
    r"C:\Games\Turtle WoW",
    r"C:\Games\TurtleWoW",
    r"D:\Turtle WoW",
    r"D:\TurtleWoW",
    r"D:\Games\Turtle WoW",
    r"D:\Games\TurtleWoW",
    r"D:\Games\WoW",
    r"E:\Turtle WoW",
    r"E:\TurtleWoW",
]

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_or_create_config() -> dict | None:
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print(f"[TurtleDink] Created default config at: {CONFIG_FILE}")
        print("[TurtleDink] Please edit config.json and fill in:")
        print("             - discord_webhook_url")
        print("             - wow_path (leave empty to auto-detect)")
        return None

    with open(CONFIG_FILE, encoding="utf-8") as f:
        config = json.load(f)

    changed = False
    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value
            changed = True
    if changed:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    if not config.get("discord_webhook_url"):
        print("[TurtleDink] ERROR: discord_webhook_url is not set in config.json")
        return None

    return config


def find_wow_path(configured_path: str) -> str | None:
    if configured_path and os.path.isdir(configured_path):
        return configured_path
    for path in CANDIDATE_WOW_PATHS:
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "WoW.exe")):
            print(f"[TurtleDink] Auto-detected Turtle WoW at: {path}")
            return path
    return None


# ---------------------------------------------------------------------------
# SavedVariables parsing
# ---------------------------------------------------------------------------

def find_saved_vars_files(wow_path: str) -> list[str]:
    pattern = os.path.join(
        wow_path, "WTF", "Account", "*", "SavedVariables", "TurtleDink.lua"
    )
    return glob.glob(pattern)


def _extract_string(block: str, key: str) -> str | None:
    m = re.search(r'\["' + re.escape(key) + r'"\]\s*=\s*"([^"]*)"', block)
    return m.group(1) if m else None


def _extract_int(block: str, key: str) -> int | None:
    m = re.search(r'\["' + re.escape(key) + r'"\]\s*=\s*(\d+)', block)
    return int(m.group(1)) if m else None


def _split_top_level_blocks(text: str) -> list[str]:
    blocks, depth, start = [], 0, -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                blocks.append(text[start : i + 1])
                start = -1
    return blocks


def parse_events(filepath: str) -> list[dict]:
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError:
        return []

    m = re.search(
        r'"pendingEvents"\]\s*=\s*\{(.*?)\},?\s*(?:\n\}|$)',
        content,
        re.DOTALL,
    )
    if not m:
        return []

    events = []
    for block in _split_top_level_blocks(m.group(1)):
        event_id   = _extract_string(block, "id")
        event_type = _extract_string(block, "type")
        player     = _extract_string(block, "player")
        level      = _extract_int(block, "level")
        if not (event_id and event_type and player and level):
            continue
        events.append({
            "type":   event_type,
            "id":     event_id,
            "player": player,
            "level":  level,
            "class":  _extract_string(block, "class") or "Unknown",
            "race":   _extract_string(block, "race")  or "Unknown",
        })
    return events


# ---------------------------------------------------------------------------
# Processed-event tracking
# ---------------------------------------------------------------------------

def load_processed_ids() -> set:
    if not PROCESSED_FILE.exists():
        return set()
    try:
        with open(PROCESSED_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_processed_ids(ids: set) -> None:
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f)


# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------

def format_message(template: str, event: dict) -> str:
    return (
        template
        .replace("{player}", event["player"])
        .replace("{level}",  str(event["level"]))
        .replace("{class}",  event.get("class", "Unknown"))
        .replace("{race}",   event.get("race",  "Unknown"))
    )


def send_discord_notification(webhook_url: str, event: dict, config: dict) -> bool:
    description = format_message(
        config.get("message_template", DEFAULT_CONFIG["message_template"]),
        event,
    )

    if config.get("use_embed", True):
        payload = {
            "embeds": [
                {
                    "title":       "Level Up!",
                    "description": description,
                    "color":       config.get("embed_color", DEFAULT_CONFIG["embed_color"]),
                    "fields": [
                        {"name": "Class", "value": event.get("class", "Unknown"), "inline": True},
                        {"name": "Race",  "value": event.get("race",  "Unknown"), "inline": True},
                    ],
                    "footer":    {"text": "TurtleDink \u2022 Turtle WoW"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
    else:
        payload = {"content": description}

    try:
        r = requests.post(webhook_url, json=payload, timeout=10)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[TurtleDink] ERROR sending Discord notification: {e}")
        return False


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  TurtleDink Companion - Discord notifications for Turtle WoW")
    print("=" * 60)

    config = load_or_create_config()
    if config is None:
        input("\nPress Enter to exit...")
        sys.exit(1)

    wow_path = find_wow_path(config.get("wow_path", ""))
    if wow_path is None:
        print("[TurtleDink] ERROR: Could not find Turtle WoW installation.")
        print("             Set 'wow_path' in config.json to your WoW folder.")
        input("\nPress Enter to exit...")
        sys.exit(1)

    interval = config.get("check_interval_seconds", DEFAULT_CONFIG["check_interval_seconds"])
    print(f"[TurtleDink] WoW path      : {wow_path}")
    print(f"[TurtleDink] Poll interval : {interval}s")
    print()
    print("[TurtleDink] Watching for level-up events. Press Ctrl+C to stop.")
    print("[TurtleDink] NOTE: Events are sent after you log out or /reload in-game.\n")

    processed_ids = load_processed_ids()
    file_mtimes: dict[str, float] = {}

    while True:
        try:
            for filepath in find_saved_vars_files(wow_path):
                try:
                    mtime = os.path.getmtime(filepath)
                except OSError:
                    continue

                if file_mtimes.get(filepath) == mtime:
                    continue

                file_mtimes[filepath] = mtime
                events = parse_events(filepath)
                new_events = [e for e in events if e["id"] not in processed_ids]

                for event in new_events:
                    if event["type"] != "levelup":
                        continue

                    ts = datetime.now().strftime("%H:%M:%S")
                    print(
                        f"[{ts}] Level-up: {event['player']} "
                        f"({event.get('race','?')} {event.get('class','?')}) -> level {event['level']}"
                    )

                    if send_discord_notification(config["discord_webhook_url"], event, config):
                        print(f"         Discord notification sent!")
                        processed_ids.add(event["id"])
                        save_processed_ids(processed_ids)
                    else:
                        print(f"         Will retry on next check.")

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n[TurtleDink] Stopped.")
            break
        except Exception as e:
            print(f"[TurtleDink] Unexpected error: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    main()
