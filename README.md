# JOCKO

## Warning

**This project is 100% vibe-coded. It is not robust, not complete, and not supported or maintained to any production standard.**

In the interest of efficiency and achieving an MVP as fast as possible, quality, robustness, and long-term maintainability were knowingly deprioritised.

This is an experimental, exploratory build — not a polished or supported product.
You are free to use it under the terms of the MIT License, but do so at your own risk.

That said, contributions, issues, and improvements are welcome. If you spot a problem or have an idea, feel free to open an issue or submit a PR — I’ll address things where time and interest permit, but no guarantees.

## About

**Jocko** is an automated accountability system designed for people who are tired of breaking promises to themselves. Named after Jocko Willink, author of *Discipline Equals Freedom*, it operates on a simple principle: **you pre-commit to specific actions, and you pay a penalty if you fail.** The system removes ambiguity and the potential to abscond by creating concrete daily and weekly commitments, tracking them automatically (via Garmin App), assessing their veracity, and enforcing consequences if you don't show up. It also integrates the mindfulness practice of delivering a page from *The Daily Stoic - Ryan Holiday* every day.

The architecture is built in layers:

1. **Data Ingestion** — Continuously pulls activity data from Garmin Connect (workouts, heart rate, body battery, sleep, steps)
2. **Memory** — Maintains persistent storage of your goals, training history, daily commitments, and conversation context
3. **Decision Engine** — Analyzes metrics and trends to determine goal compliance and coaching interventions
4. **Language Layer** — Generates context-aware coaching messages via OpenAI, shaped by your intensity setting and live data
5. **Accountability Layer** — Automatically sends pre-committed funds to a nominated recipient if weekly goals are missed
6. **Communication Layer** — Delivers coaching via Telegram with two-way conversation and proactive prompting throughout the day

---

### How It Works

The system runs on a daily commitment loop:

**Evening Planning:** Each night, the coach asks for tomorrow's wake-up time and gym time. The phrasing varies naturally through AI generation, shaped by your intensity setting — from warm and supportive at low intensity to blunt and confrontational at high intensity.

**Morning Execution:** At your nominated wake-up time, the coach fires a wake-up message that includes that day's passage from *The Daily Stoic* — a philosophical prompt to frame your mindset for the day.

**Accountability Checkpoints:** At your committed gym time, the system checks your Garmin data. If no session is logged within the expected window, the coach initiates contact based on your frequency and intensity settings — from gentle reminders to aggressive confrontation.

**Weekly Enforcement:** At week's end, the system evaluates goal compliance. If you missed your targets, a PayPal payment is automatically sent to your nominated recipient (a friend, family member, or charity). If you hit your goals, your money stays with you.

**Conversational Context:** You can message the bot at any time. It responds with full awareness of your training data, recent commitments, conversation history, and configured tone. The coach remembers what you said and holds you to it.

### The Intensity Scale

| Level | Character |
|---|---|
| 1-3 | Warm, conversational — like a supportive friend checking in |
| 4-6 | Direct and businesslike — always to the point |
| 7-9 | Blunt, impatient, occasionally cutting |
| 10 | Full Jocko Willink. Terse, aggressive, creative insults |

### Daily Rhythm

| Time | Action |
|---|---|
| Evening | Coach asks for tomorrow's wake-up and gym time |
| Wake-up time | Wake-up message + Daily Stoic passage (can override Android silent mode via Tasker) |
| Gym time + 120min | Coach checks in — session logged or not |
| Midday | If no session and frequency ≥ 7, nudge sent |
| Evening | If no session and goal at risk, warning sent. Then asks again for tomorrow. |
| Sunday evening | Pre-week planning — what days are you training? |
| Week end | Goal evaluated, PayPal payment triggered if missed |

### Data Veracity

The system validates workout data to prevent gaming. Activities are analyzed for heart rate consistency, duration vs. effort, and historical patterns. Suspicious data is flagged and the coach factors this into accountability conversations.

---

## Workout Data Veracity

The system validates workout data to prevent fake or manipulated entries. You can't just log a 5-minute "run" with no heart rate elevation and have it count toward your goals.

**`data_quality.py` analyzes each activity:**

| Check | What it looks for |
|---|---|
| Heart rate consistency | Unusually low avg HR for activity type suggests fake data |
| Duration vs effort | 2-hour session with avg HR of 80bpm is suspicious |
| Activity pattern | Flatlined HR for extended periods indicates stopped recording or manual entry |
| Historical comparison | Sudden 300% improvement without gradual progression flags review |

**When suspicious data is detected:**
- Activity is flagged in the `flags` table
- Coach is notified and factors this into weekly report
- User receives warning: *"That 'run' on Tuesday shows avg HR of 72bpm. Either your watch malfunctioned or you're gaming the system. Which is it?"*
- Repeated flags escalate intensity of accountability conversations

This prevents the easy out of just logging fake workouts to avoid penalties.

---

## Daily Stoic

Each morning wake-up message includes that day's passage from The Daily Stoic — title, quote, and reflection — delivered as part of the same message the coach uses to get you out of bed.

**Implementation:**

All 366 entries are stored locally in `stoic.py` as a dictionary keyed by month and day.  The correct entry is looked up by today's date and appended to the wake-up message.

```
wake-up message (AI-generated, intensity-shaped, Tasker trigger)
    +
Daily Stoic — [Title]
"[Quote]"
— [Author]

[Reflection]
```

**Source:** The full 366-entry dataset is included in `stoic.py`. No additional setup required.

---

## Android Alarm Override

Telegram alone cannot override Android silent mode. Two options, ordered by effort:

### Option 1 — Tasker (recommended, no custom app)

Tasker is an Android automation app. Configure it to watch for a Telegram message containing a specific trigger word (e.g. `WAKE_UP`) and fire a full-volume alarm regardless of silent or DND mode. The coach sends the trigger word as part of its wake-up message. Tasker intercepts it and fires the alarm.

**Setup steps:**
1. Install Tasker on your Android device
2. Create a profile that triggers on a Telegram notification containing `WAKE_UP`
3. Set the task to play an alarm sound at full volume
4. The coach's wake-up message always includes `WAKE_UP` as a trigger token

No custom app required. Works on all Android versions.

### Option 2 — Companion Android app (future phase)

A small Android app using Android's `ALARM` notification channel, which bypasses silent and DND by default — the same mechanism alarm clock apps use. The coach sends a webhook or Telegram trigger, the app fires the alarm.

More reliable long-term, but requires building and sideloading an app.

**Recommended path:** Start with Tasker. Build the companion app later if needed.

---

## Conversational Coaching

You can message the bot at any time and it will respond as your coach — with full awareness of your training data, goals, recent conversation history and tone setting.

**How it works:**

1. You send any message to the Telegram bot
2. `coach.py` pulls your current week's activity data, goal status, tone setting and the last 10 messages from the `conversations` table
3. All of this is injected into an OpenAI system prompt that defines the coach's personality and context
4. OpenAI generates a response in character as your coach
5. The response is sent back via Telegram and both sides of the conversation are saved to the database

**The system prompt provides the coach with:**
- Your current week's session count and sprint count vs goals
- Compliance percentage per active goal
- Trend vs previous week (session count)
- Total time and avg HR this week
- Latest body battery reading — used as coaching colour (push harder / consider recovery)
- Your last 10 messages for conversational continuity
- Your committed wake-up and gym time for tomorrow
- Current intensity level

**Body battery is not a goal.** It is context. The coach uses it to colour its language — low battery might soften a push, high battery removes any excuse.

**Example exchange:**
```
You:   I skipped my sprint session today, felt exhausted
Coach: You've done 3 sessions this week. You need 4.
       Body battery is at 38% — that tracks. But you've
       still got two days. What's the plan?
```

**AI model:** OpenAI GPT-4o (already in the stack — no additional API needed)

---

## Proactive Prompting

The coach does not wait for you to message it. Based on your frequency setting and training data, it initiates contact throughout the day. The tone of every message is shaped by your intensity setting.

**Trigger types:**

| Trigger | Condition | Example message |
|---|---|---|
| Wake-up call | Your nominated wake-up time | "Get up. You said 6am. It's 6am." |
| Gym check-in | Your nominated gym time | "You said you'd be at the gym by now. Are you?" |
| Midday nudge | No session logged by midday (frequency ≥ 7) | "Still no session. What's going on?" |
| Evening warning | No session logged, goal at risk (frequency ≥ 4) | "If you don't log a session today you'll be in breach of your commitment." |
| Evening planning | Every evening (frequency ≥ 1) | "What time do you want me to wake you up tomorrow?" |
| Pre-week planning | Sunday evening (frequency ≥ 1) | "What days are you training this week?" |
| Breach alert | Goal mathematically impossible (frequency ≥ 4) | "You cannot hit your goal this week. This will cost you $50." |
| Goal achieved | Weekly goal met | "Goal hit. $0 sent. Don't get comfortable." |

**All proactive messages are AI-generated** — the coach uses your live data and intensity setting to decide exactly what to say. No canned responses.

---

## Intensity and Frequency

Two independent controls. Tone and contact rate are separate things.

### Intensity (1-10) — tone only

How hard the coach speaks to you.

| Level | Tone |
|---|---|
| 1-3 | Encouraging, supportive, patient |
| 4-6 | Direct, no-nonsense, matter-of-fact |
| 7-9 | Aggressive, confrontational, zero tolerance |
| 10 | Full Jocko Willink. Relentless. Brutal. |

```
/intensity 7
```

### Frequency (1-10) — contact rate only

How often the coach initiates contact.

| Level | Behaviour |
|---|---|
| 1-3 | Wake-up + evening planning only |
| 4-6 | Above + gym check-in + evening warning if goal at risk |
| 7-9 | Above + midday nudge |
| 10 | Above + breach alerts as they occur |

```
/frequency 5
```

Both values are stored in the `settings` table. The scheduler reads frequency to decide whether to fire a prompt. The OpenAI system prompt receives intensity to set tone. They are injected independently and never coupled.

---

## Accountability Layer

When a weekly goal is missed, the system automatically sends a pre-committed PayPal payment to a nominated recipient (a person or charity of your choice).

**How it works:**

1. A penalty amount is configured and held in your PayPal Business balance
2. At the end of the week, the coach evaluates goal compliance
3. If the goal is not met, the PayPal Payouts API sends the funds to the recipient's email address
4. If the goal is met, nothing is sent
5. A Telegram notification is sent either way

**Recipient requirements:**
- Any PayPal account — you only need their email address

**Platform:** PayPal Business account with Payouts API enabled.

---

## Project Structure

```
ai-coach/
│
├── main.py          # Entry point and Telegram bot routing
├── config.py        # Credentials and constants only
├── database.py      # Storage layer only
├── garmin.py        # Garmin Connect login and data retrieval
├── coach.py         # Decision, AI logic, conversational and proactive coaching
├── goals.py         # All goal definitions, defaults, compliance logic — edit this for goals
├── payments.py      # PayPal Payouts logic
├── scheduler.py     # Automated jobs and proactive prompt triggers
├── stoic.py         # Local Daily Stoic dataset — 366 entries keyed by date
├── data_quality.py  # Workout data validation and veracity checking
│
├── data/
│   └── coach.db
│
├── requirements.txt
└── README.md
```

---

## Requirements

- Python 3.10+
- Garmin Connect account (email/password)
- Telegram Bot Token (via [@BotFather](https://t.me/BotFather))
- OpenAI API key
- PayPal Business account with Payouts API enabled
- Recipient's PayPal email address

---

## Installation

**Step 1 — Clone the repo**

```bash
git clone https://github.com/your-username/ai-coach.git
cd ai-coach
```

**Step 2 — Create virtual environment**

```bash
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # macOS/Linux
```

**Step 3 — Install dependencies**

```bash
pip install -r requirements.txt
```

---

## Configuration

Copy or create `config.py` and fill in your credentials:

```python
TELEGRAM_BOT_TOKEN = "your_token"
TELEGRAM_CHAT_ID   = "your_chat_id"

OPENAI_API_KEY = "your_key"

# Garmin Connect credentials (email/password login)
# The bot will log in and store tokens locally (~/.garminconnect)
# Tokens are valid for one year
GARMIN_EMAIL = "your_garmin_email@example.com"
GARMIN_PASSWORD = "your_garmin_password"

# Legacy API credentials (no longer used)
GARMIN_CLIENT_ID = ""
GARMIN_CLIENT_SECRET = ""
GARMIN_REFRESH_TOKEN = ""

PAYPAL_CLIENT_ID       = ""
PAYPAL_CLIENT_SECRET   = ""
PAYPAL_RECIPIENT_EMAIL = ""

CONVERSATION_HISTORY_LIMIT = 10
PENALTY_AMOUNT = 50

DB_PATH = "data/coach.db"
```

**Garmin Authentication:**
The bot uses the `garminconnect` library to log into your Garmin Connect account using your email and password. On first run, it authenticates and stores tokens locally in `~/.garminconnect`. These tokens are valid for approximately one year, so you won't need to log in again until they expire.

Goals are not set here. Edit `goals.py` to change your training goals.

Intensity, frequency, alarm times, and other runtime settings are stored in the database and controlled via Telegram — not in this file.

Never commit `config.py` to version control. Add it to `.gitignore`.

---

## Database

Uses SQLite (no server required). Tables are created automatically:

| Table | Purpose |
|---|---|
| `activities` | Garmin activity data — type, duration, HR, calories, body battery start/end |
| `goals` | Training goals — workouts/sprints (active), steps/calories/distance (placeholders) |
| `weekly_summary` | Computed weekly metrics |
| `conversations` | Stored message history for coaching context |
| `daily_commitments` | Wake-up time and gym time committed each evening |
| `penalty_log` | Record of all payments sent and goals met |
| `settings` | Runtime config — intensity, frequency, penalty amount, recipient |

---

## Data Flow

**Scheduled reports:**
```
Garmin Connect (email login)
    ↓
activities table
    ↓
weekly calculation
    ↓
weekly_summary table
    ↓
AI prompt generation
    ↓
goal compliance check
    ↓
goal met → no payment, log result
goal missed → PayPal Payout → recipient email
    ↓
Telegram message
```

**Daily commitment loop:**
```
Evening prompt → user replies with wake-up time + gym time
    ↓
saved to daily_commitments table
    ↓
scheduler creates jobs for tomorrow at those exact times
    ↓
wake-up time → stoic.py looks up today's entry by date
             → coach generates wake-up message (intensity-shaped)
             → Stoic passage appended
             → single Telegram "wake-up" message sent
gym time → coach checks Garmin for logged session
    ↓
session found → acknowledge
no session → proactive prompt based on intensity + frequency
```

**Proactive prompting:**
```
scheduler fires (wake-up / gym / midday / evening)
    ↓
coach.py reads frequency → decides whether to send
    ↓
coach.py reads intensity → sets tone
    ↓
builds context → OpenAI generates message
    ↓
Telegram message sent unprompted
```

**Conversational coaching:**
```
Telegram message from user
    ↓
coach.py pulls activity data + last 10 conversations
    ↓
structured context + intensity + message → OpenAI
    ↓
AI response saved to conversations table
    ↓
Telegram reply
```

---

## Telegram Commands

| Command | Action |
|---|---|
| `/weekly` | Generate and send weekly coaching report |
| `/status` | Show current week progress vs goals |
| `/goal` | Show all current goals |
| `/goal workouts_per_week 5` | Update weekly workout goal to 5 |
| `/goal sprints_per_week 3` | Update weekly sprint goal to 3 |
| `/goal calories_per_week 3000` | Activate calorie goal at 3000 kcal |
| `/goal distance_per_week 30` | Activate distance goal at 30 km |
| `/intensity 7` | Set coaching tone to 7 (1-10) |
| `/frequency 5` | Set contact frequency to 5 (1-10) |
| `/pull` | Manually pull latest Garmin data |
| `/penalty` | Show current penalty amount |
| `/penalty 100` | Update penalty amount to $100 |
| `/recipient` | Show current nominated recipient email |
| `/recipient email@example.com` | Update recipient email |
| any other message | Routed to conversational coach |

---

## Automation

The scheduler runs:

- **Evening (daily)** — Ask for tomorrow's wake-up time and gym time
- **Wake-up time (dynamic)** — Fire wake-up message at user's nominated time
- **Gym time (dynamic)** — Check Garmin for session, prompt if nothing logged
- **Daily (midday)** — If no session logged and frequency ≥ 7, send nudge
- **Daily (evening)** — If no session logged and goal at risk and frequency ≥ 4, send warning
- **Sunday evening** — Pre-week planning prompt
- **Weekly (end)** — Evaluate goal compliance, trigger PayPal payment if missed, send report

---

## Build Phases

**Phase 1 — Core**
- Manual Garmin import
- Telegram bot responds to `weekly`
- Weekly summary generated

**Phase 2 — Automation**
- Weekly scheduled Telegram message

**Note:** Daily auto-pull removed — data is pulled on-demand during gym check-in (Phase 7).

**Phase 3 — Intelligence**
- Fatigue scoring
- Trend slope analysis
- Fuel and calorie monitoring
- Improved AI prompt structure

**Phase 4 — Accountability**
- PayPal Payout on goal failure
- Penalty log and history via Telegram
- Configurable penalty amount and recipient

**Phase 5 — Conversational Coaching**
- Two-way coaching conversation via Telegram
- Conversation history stored and injected into prompts
- Coach responds with awareness of live training data

**Phase 6 — Proactive Prompting + Intensity/Frequency**
- Scheduler-driven proactive messages
- Intensity (1-10) controls tone independently
- Frequency (1-10) controls contact rate independently
- Both update the database instantly, no restart required
- All proactive messages AI-generated from live data

**Phase 7 — Daily Commitment, Alarms, and Daily Stoic**
- Evening prompt asks for wake-up time and gym time (wording varied by AI, register set by intensity)
- Scheduler dynamically creates jobs at user's nominated times
- Wake-up message includes today's Daily Stoic entry from local dataset
- Gym check-in fired at committed gym time
- Commitments stored in `daily_commitments` table
- `stoic.py` contains all 366 entries keyed by date — no external dependency

---

## Architecture Principles

- Each file has one responsibility
- Goal defaults live in `goals.py` — one place to edit when goals change
- Runtime goal values are stored in the database and updated via Telegram
- Intensity and frequency live in the database — change them via Telegram without restarting
- AI receives structured summaries, not raw data
- API logic is never mixed with coaching logic
- Payment logic is isolated in `payments.py` — never mixed with coaching logic
- Conversation history is stored in the database, not in memory
- Intensity and frequency are independent — tone and contact rate are never coupled
- Alarm times are dynamic — the scheduler rebuilds daily jobs from the database each evening

## Deployment

### Server Setup

The server runs the coach as a systemd service at `/opt/coach/`. The deployment uses:

- **Git repository**: Cloned directly from GitHub
- **Config**: `config.py` is kept on the server (gitignored, not in repo)
- **Data**: SQLite database and Garmin tokens persist in `data/`
- **Service**: Managed by systemd (`coach.service`)

### Updating the Server

**Option 1: Telegram Command (Easiest)**

Send `/update` to your coach bot. It will:
1. Pull latest code from GitHub
2. Show you the git output
3. Restart the service automatically

**Option 2: SSH Command**

```bash
ssh root@203.57.51.49 "cd /opt/coach && git pull origin main && systemctl restart coach"
```

**Option 3: Manual Steps**

```bash
ssh root@203.57.51.49
cd /opt/coach
git pull origin main
systemctl restart coach
systemctl status coach
```

### What Gets Updated

Files pulled from GitHub:
- `main.py`, `coach.py`, `garmin.py`, `scheduler.py`
- `database.py`, `goals.py`, `payments.py`, `data_quality.py`
- `stoic.py`, `requirements.txt`, `.gitignore`

Files that stay on the server (not in repo):
- `config.py` — your API keys and secrets
- `data/` — SQLite database and Garmin tokens
- `venv/` — Python virtual environment

---

## License

MIT
