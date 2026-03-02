#!/usr/bin/env python3
"""
TurtleDink Poller
=================
Runs on a schedule via GitHub Actions.
Scrapes turtlecraft.gg for each registered character's level.
Sends Discord webhook notifications when a level-up is detected.
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

CHARACTERS_FILE = Path(__file__).parent.parent / "characters.json"
ARMORY_URL = "https://turtlecraft.gg/armory/{realm}/{name}"
HEADERS = {"User-Agent": "TurtleDink-Bot/1.0 (github.com/TurtleDink)"}

RACE_NAMES = {
    1: "Human", 2: "Orc", 3: "Dwarf", 4: "Night Elf", 5: "Undead",
    6: "Tauren", 7: "Gnome", 8: "Troll", 9: "Goblin",
}
CLASS_NAMES = {
    1: "Warrior", 2: "Paladin", 3: "Hunter", 4: "Rogue", 5: "Priest",
    7: "Shaman", 8: "Mage", 9: "Warlock", 11: "Druid",
}

PRIMARY_PROFESSIONS = {
    "Alchemy", "Blacksmithing", "Enchanting", "Engineering",
    "Herbalism", "Leatherworking", "Mining", "Skinning", "Tailoring",
}
SECONDARY_SKILLS = {"Cooking", "First Aid", "Fishing", "Survival"}
ALL_SKILLS = PRIMARY_PROFESSIONS | SECONDARY_SKILLS


def load_characters() -> list:
    if not CHARACTERS_FILE.exists():
        return []
    with open(CHARACTERS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_characters(characters: list) -> None:
    with open(CHARACTERS_FILE, "w", encoding="utf-8") as f:
        json.dump(characters, f, indent=2)
        f.write("\n")


def scrape_character(name: str, realm: str) -> dict | None:
    url = ARMORY_URL.format(realm=quote(realm), name=quote(name))
    for attempt in range(1, 4):  # up to 3 attempts
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 404:
                print(f"  Character not found on armory (404)")
                return None
            r.raise_for_status()
            break  # success
        except requests.RequestException as e:
            print(f"  Request failed (attempt {attempt}/3): {e}")
            if attempt < 3:
                time.sleep(5)
            else:
                return None

    soup = BeautifulSoup(r.text, "html.parser")

    # Level is in <div class="level">18</div>
    level_div = soup.find("div", class_="level")
    if not level_div:
        print(f"  Could not find level element on page")
        return None
    try:
        level = int(level_div.get_text(strip=True))
    except ValueError:
        print(f"  Could not parse level value: {level_div.text!r}")
        return None

    # Attempt to get race and class from Livewire wire:snapshot JSON
    race, cls = "Unknown", "Unknown"
    snapshot_tag = soup.find(attrs={"wire:snapshot": True})
    if snapshot_tag:
        try:
            snapshot = json.loads(snapshot_tag["wire:snapshot"])
            char_list = snapshot.get("data", {}).get("character", [])
            char_data = char_list[0] if isinstance(char_list, list) and char_list else {}
            race_raw = char_data.get("race")
            cls_raw = char_data.get("class") or char_data.get("class_name")
            race = RACE_NAMES.get(race_raw, race_raw) or "Unknown"
            cls = CLASS_NAMES.get(cls_raw, cls_raw) or "Unknown"
        except (json.JSONDecodeError, KeyError, TypeError, IndexError):
            pass

    skills = _parse_skills(soup)
    return {"level": level, "race": race, "class": cls, "skills": skills}


def _parse_skills(soup) -> dict:
    """Parse skill/profession levels from the armory page.

    Each skill entry is structured as:
      <parent><img src="...SkillName-hash.png"><span>SkillName</span><span>VALUE</span></parent>
    The img alt attribute is empty, so we match on span text content instead.
    """
    skills = {}
    for span in soup.find_all("span"):
        skill_name = span.get_text(strip=True)
        if skill_name not in ALL_SKILLS:
            continue
        parent = span.parent
        if not parent:
            continue
        for sib in parent.find_all("span"):
            text = sib.get_text(strip=True).split("/")[0].strip()
            if text.isdigit():
                skills[skill_name] = int(text)
                break
    return skills


def send_discord(webhook_url: str, name: str, level: int, race: str, cls: str, realm: str) -> bool:
    embed = {
        "title": "\U0001f3c6 Level Up!",
        "description": f"**{name}** just reached level **{level}**!",
        "color": 16766720,  # Gold 0xFFD700
        "fields": [
            {"name": "Realm", "value": realm, "inline": True},
        ],
        "footer": {"text": "TurtleDink \u2022 Turtle WoW"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Only show race/class fields if we actually have them
    if race != "Unknown":
        embed["fields"].insert(0, {"name": "Race", "value": race, "inline": True})
    if cls != "Unknown":
        embed["fields"].insert(1 if race != "Unknown" else 0, {"name": "Class", "value": cls, "inline": True})

    try:
        r = requests.post(webhook_url, json={"embeds": [embed]}, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"  Discord error: {e}")
        return False


def send_discord_skill(webhook_url: str, name: str, skill: str, old_val: int, new_val: int, realm: str) -> bool:
    category = "Secondary Skill" if skill in SECONDARY_SKILLS else "Profession"
    embed = {
        "title": "\U0001f4aa Skill Up!",
        "description": f"**{name}** levelled **{skill}** to **{new_val}**!",
        "color": 2031360,  # WoW uncommon green 0x1EFF00
        "fields": [
            {"name": "Skill", "value": skill, "inline": True},
            {"name": "Type", "value": category, "inline": True},
            {"name": "Level", "value": f"{old_val} \u2192 {new_val}", "inline": True},
            {"name": "Realm", "value": realm, "inline": True},
        ],
        "footer": {"text": "TurtleDink \u2022 Turtle WoW"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        r = requests.post(webhook_url, json={"embeds": [embed]}, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"  Discord error: {e}")
        return False


def main() -> None:
    print("=== TurtleDink Poller ===")
    characters = load_characters()

    if not characters:
        print("No characters registered yet.")
        return

    print(f"Checking {len(characters)} character(s)...\n")
    changed = False

    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "")
    thread_id = os.environ.get("DISCORD_THREAD_ID", "")
    if thread_id:
        webhook = f"{webhook}?thread_id={thread_id}"

    for char in characters:
        name = char["name"]
        realm = char["realm"]
        old_level = char.get("level", 0)
        print(f"[{name}] ({realm}) last known level: {old_level}")

        data = scrape_character(name, realm)
        if data is None:
            print(f"  Skipping.\n")
            time.sleep(1)
            continue

        new_level = data["level"]

        # Update race/class if the armory gave us real values
        if data["race"] != "Unknown":
            char["race"] = data["race"]
        if data["class"] != "Unknown":
            char["class"] = data["class"]

        if old_level == 0:
            # First time we've seen this character — just record level, no notification
            print(f"  First poll: initialising at level {new_level}.")
            char["level"] = new_level
            changed = True

        elif new_level > old_level:
            print(f"  Level up detected: {old_level} -> {new_level}")
            if webhook:
                for lvl in range(old_level + 1, new_level + 1):
                    race_val = char.get("race", "Unknown")
                    cls_val = char.get("class", "Unknown")
                    success = send_discord(
                        webhook, name, lvl,
                        RACE_NAMES.get(race_val, race_val),
                        CLASS_NAMES.get(cls_val, cls_val),
                        realm,
                    )
                    if success:
                        print(f"  Discord notification sent for level {lvl}.")
                    else:
                        print(f"  Failed to notify for level {lvl} — will retry next poll.")
                    time.sleep(0.5)
            char["level"] = new_level
            changed = True

        else:
            print(f"  No change (level {new_level}).")

        # Handle skill/profession changes
        new_skills = data.get("skills", {})
        if new_skills:
            old_skills = char.setdefault("skills", {})
            for skill_name, new_val in sorted(new_skills.items()):
                old_val = old_skills.get(skill_name)
                if old_val is None:
                    # First time seeing this skill — initialise silently
                    old_skills[skill_name] = new_val
                    changed = True
                elif new_val > old_val:
                    print(f"  Skill up: {skill_name} {old_val} -> {new_val}")
                    if webhook:
                        success = send_discord_skill(webhook, name, skill_name, old_val, new_val, realm)
                        if success:
                            print(f"    Discord notification sent.")
                        else:
                            print(f"    Failed to notify — will retry next poll.")
                        time.sleep(0.5)
                    old_skills[skill_name] = new_val
                    changed = True

        print()
        time.sleep(1)  # Be polite to turtlecraft.gg

    if changed:
        save_characters(characters)
        print("characters.json updated.")
    else:
        print("No changes.")


if __name__ == "__main__":
    main()
