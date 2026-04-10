# JOCKO — Build Log

Tracks what is built, what is in progress, and what is next.
Each task is marked with its current status.

Status key:
- `[ ]` not started
- `[~]` in progress
- `[x]` complete
- `[!]` blocked — reason noted

---

## Phase 1 — Core (Build this first, nothing else)

Goal: manually pull Garmin data, generate a weekly summary, send it via Telegram on demand.
When this works end-to-end, Phase 1 is done.

| Status | Task | File | Notes |
|---|---|---|---|
| `[x]` | Create project folder structure | — | `ai-coach/` and `ai-coach/data/` created |
| `[x]` | Create virtual environment | — | `python -m venv venv` — completed |
| `[x]` | Create `requirements.txt` | `requirements.txt` | python-telegram-bot==21.9, openai==1.61.0, requests, apscheduler, garminconnect |
| `[x]` | Install dependencies | — | `venv\Scripts\pip install -r requirements.txt` — completed |
| `[x]` | Credentials and constants | `config.py` | Telegram + OpenAI + Garmin populated. PayPal populated. Added OPENAI_MODEL config. |
| `[x]` | Create all database tables | `database.py` | activities, goals, weekly_summary, conversations, daily_commitments, penalty_log, settings. Fixed goals table schema. |
| `[x]` | Garmin email/password login | `garmin.py` | Uses garminconnect library. Tokens stored in ~/.garminconnect. Fixed column name from start_date to start_time. |
| `[x]` | Garmin activity pull + dummy fallback | `garmin.py` | Dummy data seeds 8 realistic activities across 2 weeks |
| `[x]` | Goals restructured | `config.py` / `database.py` / `coach.py` | Active: workouts_per_week=4, sprints_per_week=2. Placeholders: steps, calories, distance |
| `[x]` | Weekly summary calculation | `coach.py` | Counts sessions, sprints, time, calories, avg HR. Compliance per active goal. |
| `[x]` | OpenAI weekly report generation | `coach.py` | Uses OPENAI_MODEL from config (default: gpt-4o), intensity-shaped prompt, compliance lines injected |
| `[x]` | Telegram bot setup | `main.py` | Bot token, polling loop. Added /start command with welcome message. |
| `[x]` | `weekly` command handler | `main.py` | Calls `coach.generate_weekly_report()`, sends result |
| `[x]` | `status` command handler | `main.py` | Shows current week compliance |
| `[x]` | `goal` command handler | `main.py` | `/goal workouts_per_week 5` — supports all goal keys |
| `[x]` | `intensity` / `frequency` command handlers | `main.py` | Updates settings table instantly |
| `[x]` | `penalty` / `recipient` command handlers | `main.py` | Manage PayPal penalty config |
| `[x]` | `/pull` command handler | `main.py` | Manual Garmin pull on demand |
| `[x]` | Free-text handler | `main.py` | All non-commands routed to `coach.chat()`. Added debug logging. |
| `[x]` | End-to-end test | — | Bot running, receiving messages. OpenAI API quota resolved - billing active. |

**To run Phase 1 — completed:**
```powershell
cd ai-coach
python -m venv venv
venv\Scripts\pip install -r requirements.txt
python main.py
```

**Current Status:**
- Bot is running in terminal 11
- All dependencies installed (python-telegram-bot==21.9, openai==1.61.0, garminconnect==0.2.38)
- Database schema fixed and operational
- Telegram integration working - bot receives and processes messages
- Character prompt consolidated to Jocko Willink
- Configurable OpenAI model (OPENAI_MODEL in config.py)
- OpenAI billing active - API quota issue resolved
- Ready for full end-to-end testing

**End-to-end test checklist:**
- [x] Bot starts without errors
- [x] Bot receives Telegram messages (confirmed via debug logs)
- [x] Send `/start` — welcome message works
- [x] Send `/pull` — Garmin data pull works
- [x] Send `/status` — week summary appears
- [x] Send `/weekly` — AI coaching report received
- [x] Send a free-text message — coach replies in character
- [x] Send `/goal` — current goals displayed
- [x] Send `/intensity 8` — intensity updated

**Phase 1 Status: COMPLETE**

**Known Issues:**
None. Phase 1 complete and tested.

---

## Phase 2 — Automation

Goal: system runs itself. No manual triggers needed.

| Status | Task | File | Notes |
|---|---|---|---|
| `[x]` | Weekly report job | `scheduler.py` | Fires end of week, sends report via Telegram |
| `[x]` | Scheduler startup | `main.py` | Start scheduler alongside bot |
| `[x]` | End-to-end test | — | Confirm auto-report fires correctly |

**Additional dependency:**
```
apscheduler
```

**Note:** Daily Garmin pull removed — data is pulled on-demand during gym check-in (Phase 7).

**Phase 2 Status: COMPLETE**

---

## Phase 3 — Intelligence

Goal: coach understands trends, not just totals.

| Status | Task | File | Notes |
|---|---|---|---|
| `[x]` | Fatigue scoring | `coach.py` | Based on avg HR trend and session density |
| `[x]` | Trend slope calculation | `coach.py` | Week-on-week distance delta |
| `[x]` | Body battery ingestion | `garmin.py` | Pull body battery from Garmin if available |
| `[x]` | Improved prompt structure | `coach.py` | Inject fatigue score, trend, body battery into OpenAI prompt |
| `[x]` | End-to-end test | — | Confirm richer coaching output |

**Phase 3 Status: COMPLETE**

---

## Phase 4 — Accountability

Goal: missed goals cost money automatically.

| Status | Task | File | Notes |
|---|---|---|---|
| `[x]` | PayPal OAuth setup | `payments.py` | Client credentials flow, access token |
| `[x]` | PayPal Payout function | `payments.py` | Send funds to recipient email via Payouts API. Sandbox=$1, Live=uses config.PENALTY_AMOUNT |
| `[x]` | Goal compliance check | `coach.py` | `check_goal_compliance()` evaluates at week end — met or missed |
| `[x]` | Trigger payout on miss | `scheduler.py` | `check_and_apply_penalty()` job Sundays 11:59 PM. Calls `payments.send_penalty()` if goal missed |
| `[x]` | Log result | `database.py` | `log_penalty()` writes to penalty_log table |
| `[x]` | `penalty` command handler | `main.py` | Shows current penalty amount from database |
| `[x]` | `penalty <n>` command handler | `main.py` | Updates both database AND `config.PENALTY_AMOUNT` |
| `[x]` | `recipient` command handler | `main.py` | Updates both database AND `config.PAYPAL_RECIPIENT_EMAIL` |
| `[x]` | End-to-end test | — | $1 AUD payout sent successfully (Batch ID: U36UQGK2LGLTG) |

**Additional dependency:**
```
paypalrestsdk==1.13.3
```

**To switch to live mode:**
Edit `payments.py` line 6:
```python
PAYPAL_MODE = "live"  # Change from "sandbox"
```

In live mode, the penalty amount from `/penalty <n>` command is used. In sandbox mode, always $1.

**Phase 4 Status: COMPLETE**

---

## Phase 5 — Conversational Coaching

Goal: talk to the coach any time via Telegram.

| Status | Task | File | Notes |
|---|---|---|---|
| `[x]` | Conversation history storage | `database.py` | Save both sides of every exchange to conversations table |
| `[x]` | Context builder | `coach.py` | Pull last 10 exchanges + activity data + intensity into prompt |
| `[x]` | Conversational response function | `coach.py` | `coach.chat(user_message)` — returns AI response |
| `[x]` | Free-text message handler | `main.py` | Any non-command message routed to `coach.chat()` |
| `[x]` | End-to-end test | — | Send several messages, confirm coach responds with context awareness |

**Phase 5 Status: COMPLETE**

---

## Phase 6 — Proactive Prompting + Intensity / Frequency

Goal: coach initiates contact. Tone and frequency independently configurable.

| Status | Task | File | Notes |
|---|---|---|---|
| `[x]` | Seed settings table | `database.py` | Default intensity=5, frequency=5 on first run (lines 118-125) |
| `[x]` | `intensity <n>` command handler | `main.py` | Updates settings table instantly (lines 54-60) |
| `[x]` | `frequency <n>` command handler | `main.py` | Updates settings table instantly (lines 62-68) |
| `[x]` | Intensity injected into all prompts | `coach.py` | Every OpenAI call reads intensity from settings (lines 200, 253) |
| `[x]` | Morning check-in job | `scheduler.py` | Fires daily at 7:00 AM, frequency >= 1 |
| `[x]` | Midday nudge job | `scheduler.py` | Fires at 12:00 PM if no session logged, frequency >= 7 |
| `[x]` | Evening warning job | `scheduler.py` | Fires at 6:00 PM if no session and goal at risk, frequency >= 4 |
| `[x]` | Breach alert | `scheduler.py` | Fires at 8:00 PM if goal mathematically impossible, frequency >= 4 |
| `[x]` | Sunday pre-week planning prompt | `scheduler.py` | Fires Sunday at 7:00 PM, frequency >= 1 |
| `[x]` | End-to-end test | — | Set intensity 9, frequency 9 — confirm tone and volume |

**Phase 6 Status: COMPLETE**

---

## Phase 7 — Daily Commitment, Alarms, and Daily Stoic

Goal: coach owns your morning. You commit the night before. It holds you to it.

| Status | Task | File | Notes |
|---|---|---|---|
| `[x]` | Build Daily Stoic dataset | `stoic.py` | 366 entries as dict keyed by (month, day) — title, quote, author, reflection |
| `[x]` | Stoic lookup function | `stoic.py` | `get_entry(date)` returns today's entry |
| `[x]` | Evening commitment prompt | `scheduler.py` | Fires each evening — AI asks for wake-up time and gym time, wording shaped by intensity |
| `[x]` | Parse and save commitment reply | `main.py` | Detect time replies, save to daily_commitments table |
| `[x]` | Dynamic wake-up job | `scheduler.py` | Reads tomorrow's wake-up time from daily_commitments, schedules job |
| `[x]` | Wake-up message with Stoic | `coach.py` | AI wake-up message (intensity-shaped) + Stoic entry appended + WAKE_UP trigger token |
| `[x]` | Dynamic gym check-in job | `scheduler.py` | Reads gym time +120min from daily_commitments, schedules job |
| `[x]` | Gym check-in logic | `coach.py` | Check Garmin for session within window — respond accordingly |
| `[x]` | Tasker setup guide | `TASKER_SETUP.md` | Document Tasker profile for WAKE_UP token → alarm override |
| `[ ]` | End-to-end test | — | Full evening → morning → gym cycle |

**Phase 7 Status:** Coding complete, end-to-end test pending

---

## Phase 8 — Deployment & Server Setup

Goal: Deploy to production server, set up git repository, configure environment.

| Status | Task | File | Notes |
|---|---|---|---|
| `[x]` | Initialize git repository | `.git/` | Created, initial commit done |
| `[x]` | Create .gitignore | `.gitignore` | Exclude venv, data files, __pycache__, .env |
| `[x]` | Create config.py.example | `config.py.example` | Template with placeholder values |
| `[x]` | Update config.py for env vars | `config.py` | Read secrets from environment variables |
| `[x]` | Create .env.example | `.env.example` | Document all required environment variables |
| `[x]` | Create deploy.sh script | `deploy.sh` | Script to deploy code to server |
| `[x]` | Create DEPLOY.md documentation | `DEPLOY.md` | Step-by-step deployment guide |
| `[x]` | Commit all source code | — | Initial commit done: "Jocko AI Coach complete through Phase 7" |
| `[x]` | Server SSH setup | — | SSH keys configured |
| `[x]` | Deploy to server | — | Code copied to /opt/coach on jocko.ai (203.57.51.49) |
| `[x]` | Configure systemd service | `/etc/systemd/system/coach.service` | Service name: coach, auto-starts on boot |
| `[x]` | Set up environment variables | — | .env file created on server with real secrets |
| `[x]` | Configure firewall | — | UFW inactive, no firewall blocking |
| `[x]` | End-to-end test | — | Bot running and responding on server |

**Phase 8 Status: COMPLETE**



## Decisions Log

Decisions made during build that future-you should know about.

| Date | Decision | Reason |
|---|---|---|
| — | SQLite over Postgres | Personal use, no server required, built into Python |
| — | OpenAI GPT-4o over local LLM | Already in stack, no setup overhead, quality |
| — | PayPal over Stripe/Kraken | Already have PayPal Business, simplest Payouts API |
| — | Local Stoic dataset over scraping | No external dependency, no failure at 5am |
| — | Tasker over companion app for alarm | Fastest path, no app build required |
| — | Intensity and frequency decoupled | Tone and contact rate are independent user preferences |

---

## Blockers

None currently.

---

## Known Issues

1. `[x]` Jocko missed wakeup call 19/03/26 — Wake-up job did not fire as scheduled
2. `[x]` Jocko produced the stoic passage on 18/03/26 but failed to attach the "reflection" — Stoic entry missing reflection text
3. `[x]` Jocko seems to have no awareness — Possibly a prompt issue? Bot lacks self-knowledge about being a bot built by user and basic understanding of how it works (database, architecture)
4. `[x]` Jocko not producing wakeup calls — Wake-up job not firing as scheduled
5. `[x]` Jocko still rambling despite the cap on number of sentences — Response length control not working
6. `[x]` /activate command produces no response — Command handler not functioning? should notify of penalty start date

---

## Phase 9 — Timezone Handling

Goal: All times stored in UTC, converted to user timezone for display and scheduling.

**Background:**
- Garmin provides `startTimeLocal` (user's local time) and `startTimeGMT` (UTC)
- Current code strips timezone info, causing incorrect time comparisons
- Scheduler uses naive datetimes, unreliable for daily commitments

**Approach:** Hybrid - Garmin-derived timezone with config fallback

**Priority Order:**
1. **Primary:** Derive timezone from latest Garmin activity (handles travel, DST changes)
2. **Fallback:** Use `USER_TIMEZONE` from config if no activities exist or derivation fails

| Status | Task | File | Notes |
|---|---|---|---|
| `[x]` | Add USER_TIMEZONE config setting | `config.py` | IANA timezone name (e.g., "Australia/Sydney") - used as fallback |
| `[x]` | Add timezone field to settings table | `database.py` | Store detected/derived timezone |
| `[x]` | Create timezone utility module | `timezone.py` | UTC conversion, local time formatting, TZ detection |
| `[x]` | Update garmin.py to capture both time fields | `garmin.py` | Store `startTimeGMT` as UTC, derive offset from `startTimeLocal` |
| `[x]` | Update database schema for UTC storage | `database.py` | Ensure start_time stores ISO 8601 UTC format |
| `[x]` | Update coach.py to use UTC internally | `coach.py` | Convert UTC → local only for display |
| `[x]` | Update scheduler to use timezone-aware datetimes | `scheduler.py` | Schedule jobs in user's local timezone |
| `[x]` | Add /timezone command | `main.py` | Allow user to view/update timezone manually |
| `[x]` | Auto-update timezone on each Garmin pull | `timezone.py` | Re-derive from latest activity, update settings table |
| `[x]` | Test timezone conversions | — | Verified UTC storage, local display, scheduling accuracy |

**Phase 9 Status: COMPLETE**

---

## Session Notes

Use this section to record what was done each session so you can pick up exactly where you left off.

| Session | What was done | Next step |
|---|---|---|
| — | README and BUILDLOG created | Start Phase 1: project setup and config.py |
| — | Phase 1 completed | Start Phase 2: automation |
| — | Phase 2 completed | Start Phase 3: intelligence |
| — | Phase 3 completed | Start Phase 4: accountability |
| — | Phase 4 completed | Start Phase 5: conversational coaching |
| — | Phase 5 completed | Start Phase 6: proactive prompting |
| — | Phase 6 completed | Start Phase 7: daily commitment, alarms, stoic |
| — | Phase 7 coding completed | Run end-to-end test, then git setup and server deploy |
| — | BUILDLOG refactored | Continue Phase 8 deployment |
| — | Phase 8 deployment completed | Start Phase 9: timezone handling |

---

**Implementation Details:**

1. **Storage Format:** All times stored as ISO 8601 UTC (e.g., `2026-03-19T08:30:00+00:00`)

2. **Timezone Detection Logic:**
   ```python
   # From Garmin activity data
   local = activity['startTimeLocal']   # "2026-03-19T18:30:00"
   gmt = activity['startTimeGMT']       # "2026-03-19T08:30:00"
   # Calculate offset, map to IANA timezone
   ```

3. **Scheduling:** APScheduler jobs use `tz` parameter with user's timezone

4. **Display:** Convert UTC → local timezone only when generating messages

**Dependencies:**
```
# zoneinfo is built into Python 3.9+, no external dependency needed
# For Python < 3.9: backports.zoneinfo
```
