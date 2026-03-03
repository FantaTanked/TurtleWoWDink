# TurtleDink

Discord level-up notifications for [Turtle WoW](https://turtle-wow.org), inspired by [Dink for RuneLite](https://github.com/pajlads/DinkPlugin).

When you level up, a notification is automatically posted to your Discord channel. No companion app, no Python, nothing running on your machine — install the addon once and register once.

---

## How It Works

1. A GitHub Actions job runs every 15 minutes via cron and checks [turtlecraft.gg/armory](https://turtlecraft.gg/armory) for each registered character's level / professions.
2. When a level-up is detected, it sends a Discord webhook notification.

---

## Player Setup

### Register your character

[Open a registration issue](../../issues/new?template=register.yml) in this repository and fill in:

- Your character name (exact spelling, case-sensitive)
- Your realm (Nordanaar, Tel'Abim, or Ambershire)
- Your Discord webhook URL

A bot will process it automatically within a minute. Your character will be picked up on the next poll (within 15 minutes). No notification is sent for your current level — only future level-ups.
