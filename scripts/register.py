#!/usr/bin/env python3
"""
TurtleDink Registration Handler
================================
Called by the GitHub Actions register workflow when a player opens
a registration issue. Parses the issue body and adds the character
to characters.json, then writes a result file for the workflow to use.
"""

import json
import os
import re
import sys
from pathlib import Path

CHARACTERS_FILE = Path(__file__).parent.parent / "characters.json"
RESULT_FILE = Path(__file__).parent.parent / "registration_result.json"

VALID_REALMS = {"Nordanaar", "Tel'Abim", "Ambershire"}


def load_characters() -> list:
    if not CHARACTERS_FILE.exists():
        return []
    with open(CHARACTERS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_characters(characters: list) -> None:
    with open(CHARACTERS_FILE, "w", encoding="utf-8") as f:
        json.dump(characters, f, indent=2)
        f.write("\n")


def write_result(success: bool, comment: str, close_issue: bool = True) -> None:
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump({"success": success, "comment": comment, "close_issue": close_issue}, f)


def parse_issue_body(body: str) -> dict | None:
    """
    GitHub form-based issue templates produce a body like:

        ### Character Name

        Jimmybowman

        ### Realm

        Nordanaar
    """
    name_match = re.search(r"### Character Name\s+(\S[^\n]*)", body)
    realm_match = re.search(r"### Realm\s+(\S[^\n]*)", body)

    if not (name_match and realm_match):
        return None

    name = name_match.group(1).strip()
    realm = realm_match.group(1).strip()

    if realm not in VALID_REALMS:
        return None

    if not name or len(name) > 12:
        return None

    return {"name": name, "realm": realm}


def main() -> None:
    body = os.environ.get("ISSUE_BODY", "")
    issue_title = os.environ.get("ISSUE_TITLE", "")

    # Only process registration issues
    if not issue_title.lower().startswith("register:"):
        print("Issue is not a registration request — skipping.")
        write_result(False, "", close_issue=False)
        sys.exit(0)

    parsed = parse_issue_body(body)
    if not parsed:
        write_result(
            success=False,
            comment=(
                "Could not parse your registration. Please use the issue template and fill in "
                "all fields.\n\n"
                "**Valid realms:** Nordanaar, Tel'Abim, Ambershire"
            ),
            close_issue=False,
        )
        print("ERROR: Could not parse registration issue body.")
        sys.exit(1)

    name = parsed["name"]
    realm = parsed["realm"]

    characters = load_characters()

    # Check for existing registration
    for char in characters:
        if char["name"].lower() == name.lower() and char["realm"] == realm:
            print(f"Already registered: {name} on {realm}.")
            write_result(
                success=True,
                comment=f"**{name}** on **{realm}** is already registered!",
            )
            return

    # New registration — level starts at 0 (poll.py will initialise on first check)
    characters.append({
        "name": name,
        "realm": realm,
        "level": 0,
        "race": "Unknown",
        "class": "Unknown",
    })
    save_characters(characters)
    print(f"Registered {name} on {realm}.")
    write_result(
        success=True,
        comment=(
            f"Registered **{name}** on **{realm}**! "
            f"You will receive Discord notifications on every level-up.\n\n"
            f"> Your character will be picked up on the next poll (within 5 minutes). "
            f"No notification is sent for your current level — only future level-ups."
        ),
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Always write a result file so the workflow step doesn't fail trying to read it
        write_result(
            success=False,
            comment=f"Registration failed due to an internal error: `{e}`\n\nPlease contact the repo owner.",
            close_issue=False,
        )
        print(f"FATAL: {e}")
        sys.exit(1)
