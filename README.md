# TurtleDink

Discord level-up notifications for [Turtle WoW](https://turtle-wow.org), inspired by [Dink for RuneLite](https://github.com/pajlads/DinkPlugin).

When you level up, a notification is automatically posted to your Discord channel. No companion app, no Python, nothing running on your machine — install the addon once and register once.

---

## How It Works

1. A GitHub Actions job runs every 5 minutes and checks [turtlecraft.gg/armory](https://turtlecraft.gg/armory) for each registered character's level.
2. When a level-up is detected, it sends a Discord webhook notification.
3. The in-game addon shows a chat message on ding — Discord is handled entirely by this repo.

---

## Player Setup

### Step 1 — Install the addon (optional, for in-game chat message on ding)

Copy the `TurtleDink` folder into your WoW addons directory:

```
<Turtle WoW>\Interface\AddOns\TurtleDink\
```

Enable it in-game from the AddOns menu on the character select screen.

**Slash commands:**

| Command | Description |
|---|---|
| `/tdink help` | Show commands |
| `/tdink enable` | Enable in-game level-up message |
| `/tdink disable` | Disable in-game level-up message |
| `/tdink status` | Show whether messages are enabled |

### Step 2 — Create a Discord webhook

1. Open your Discord server
2. Go to **Server Settings → Integrations → Webhooks**
3. Click **New Webhook**, give it a name, choose a channel
4. Click **Copy Webhook URL**

### Step 3 — Register your character

[Open a registration issue](../../issues/new?template=register.yml) in this repository and fill in:

- Your character name (exact spelling, case-sensitive)
- Your realm (Nordanaar, Tel'Abim, or Ambershire)
- Your Discord webhook URL

A bot will process it automatically within a minute. Your character will be picked up on the next poll (within 5 minutes). No notification is sent for your current level — only future level-ups.

### To update your webhook

Open a new registration issue with the same character name and realm but your new webhook URL. The old one will be replaced automatically.

---

## Repository Owner Setup

> Do this once after creating the repo on GitHub.

1. **Make the repository public.** GitHub Actions scheduled workflows run free with no minute limits on public repos.

2. **Create the `registration` label.** Go to Issues → Labels → New label, name it `registration`. The issue template applies this label automatically.

3. **Ensure Actions are enabled.** Go to Settings → Actions → General → Allow all actions.

4. **Test the poller manually.** Go to Actions → "Poll Character Levels" → Run workflow. Check the output — it will log each character but won't commit unless a level change is detected.

---

## Repository Structure

```
TurtleWoWDink/
├── TurtleDink/                  ← WoW addon — drop into Interface/AddOns/
│   ├── TurtleDink.toc
│   └── TurtleDink.lua
├── scripts/
│   ├── poll.py                  ← scrapes turtlecraft.gg, sends Discord webhooks
│   └── register.py              ← processes registration issues
├── characters.json              ← registered characters (auto-managed by bot)
├── .github/
│   ├── workflows/
│   │   ├── poll.yml             ← runs every 5 minutes
│   │   └── register.yml        ← runs when a registration issue is opened
│   └── ISSUE_TEMPLATE/
│       └── register.yml        ← the player registration form
└── companion/                   ← legacy local companion app (still works if preferred)
```

---

## Notes

- **Notification delay:** The armory on turtlecraft.gg updates when your character logs out or reloads UI. There is an inherent delay between levelling up and the notification being sent (up to ~10 minutes worst case).
- **Character not indexed:** If your character doesn't appear on turtlecraft.gg yet, wait a session or two for the armory to index it, then re-register.
- **Webhook privacy:** Your webhook URL is stored in `characters.json`, which is publicly visible in this repo. Anyone with the URL can post to your Discord channel. Regenerate it in Discord if it is ever abused.
- **Scheduled workflow delays:** GitHub may delay scheduled workflows by a few minutes during high load. This is normal and expected.
- **Addon version warning:** If you see an interface version mismatch, open `TurtleDink.toc` and update the `## Interface:` line to match the version shown on your AddOns screen.
