from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from telegram import Bot
from datetime import datetime, timedelta
import asyncio
import coach
import database
import payments
import timezone
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, PAYPAL_RECIPIENT_EMAIL

scheduler = None

# Store references to dynamic jobs so they can be rescheduled
_wakeup_job_id = "dynamic_wakeup"
_gym_checkin_job_id = "dynamic_gym_checkin"


def _parse_time_to_datetime(time_str: str, base_date=None):
    """Parse time string (HH:MM or HH:MM AM/PM) to timezone-aware datetime."""
    if base_date is None:
        base_date = timezone.now_local().date()

    time_str = time_str.strip().upper()

    try:
        if 'AM' in time_str or 'PM' in time_str:
            t = datetime.strptime(time_str, "%I:%M %p").time()
        elif ':' in time_str:
            t = datetime.strptime(time_str, "%H:%M").time()
        else:
            # HHMM format
            t = datetime.strptime(time_str, "%H%M").time()
        # Return timezone-aware datetime in user's local timezone
        return datetime.combine(base_date, t).replace(tzinfo=timezone.get_user_timezone())
    except ValueError as e:
        print(f"[scheduler] Error parsing time '{time_str}': {e}")
        return None


async def scheduled_wakeup():
    """Dynamic wake-up job - fires at user's committed wake-up time."""
    print(f"[scheduler] === WAKE-UP JOB FIRING at {timezone.now_local().isoformat()} (local) ===")
    try:
        # Check if Jocko is paused due to insufficient funds
        if database.get_setting("jocko_paused") == "1":
            print("[scheduler] Jocko is paused - skipping wake-up message")
            return

        # Check if Jocko is dormant or deactivated
        if database.get_setting("jocko_dormant") == "1":
            print("[scheduler] Jocko is dormant - skipping wake-up message")
            return
        if database.get_setting("jocko_active") != "1":
            print("[scheduler] Jocko is deactivated - skipping wake-up message")
            return

        intensity = int(database.get_setting("intensity") or 5)
        print(f"[scheduler] Current intensity: {intensity}")

        # Generate wake-up message with Stoic entry
        print("[scheduler] Generating wake-up message...")
        message = coach.generate_wakeup_message(intensity)
        print(f"[scheduler] Wake-up message generated, length: {len(message)}")

        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("[scheduler] === WAKE-UP MESSAGE SENT SUCCESSFULLY ===")
    except Exception as e:
        print(f"[scheduler] === ERROR in wake-up job: {e} ===")
        import traceback
        traceback.print_exc()


async def scheduled_gym_checkin():
    """Dynamic gym check-in job - fires 120 min after committed gym time."""
    print(f"[scheduler] Gym check-in job firing at {timezone.now_local().isoformat()} (local)")
    try:
        # Check if Jocko is paused due to insufficient funds
        if database.get_setting("jocko_paused") == "1":
            print("[scheduler] Jocko is paused - skipping gym check-in")
            return
        # Check if Jocko is dormant or deactivated
        if database.get_setting("jocko_dormant") == "1":
            print("[scheduler] Jocko is dormant - skipping gym check-in")
            return
        if database.get_setting("jocko_active") != "1":
            print("[scheduler] Jocko is deactivated - skipping gym check-in")
            return

        intensity = int(database.get_setting("intensity") or 5)

        # Get today's commitment using local date
        today_str = timezone.now_local().date().isoformat()
        commitment = database.get_daily_commitment(today_str)

        if not commitment or not commitment[1]:  # No gym time committed
            print("[scheduler] No gym commitment found for today, skipping check-in")
            return

        gym_time = commitment[1]

        # Skip if rest day
        if gym_time.upper() in ("REST", "NONE"):
            print("[scheduler] Gym is REST for today, skipping check-in")
            return

        # Pull latest Garmin data first to ensure we have the most recent activities
        print("[scheduler] Pulling latest Garmin data before check-in...")
        try:
            import garmin
            garmin.pull_activities()
            print("[scheduler] Garmin data pulled successfully")
        except Exception as pull_error:
            print(f"[scheduler] Warning: Failed to pull Garmin data: {pull_error}")

        # Check if session exists in window
        session_found = coach.check_gym_session_in_window(gym_time, window_minutes=120)

        # Generate appropriate message
        message = coach.generate_gym_checkin_message(intensity, session_found)

        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

        status = "found" if session_found else "NOT FOUND"
        print(f"[scheduler] Gym check-in complete: session {status}")
    except Exception as e:
        print(f"[scheduler] Error in gym check-in job: {e}")


def schedule_dynamic_jobs():
    """Schedule tomorrow's wake-up and gym check-in jobs based on commitments."""
    global scheduler
    if not scheduler:
        print("[scheduler] Cannot schedule dynamic jobs - scheduler not running")
        return

    try:
        # Get tomorrow's commitment using local timezone
        tomorrow = timezone.now_local().date() + timedelta(days=1)
        tomorrow_str = tomorrow.isoformat()
        print(f"[scheduler] schedule_dynamic_jobs() called - looking for commitment on {tomorrow_str}")
        commitment = database.get_daily_commitment(tomorrow_str)

        if not commitment:
            print(f"[scheduler] No commitment found for {tomorrow_str}")
            return

        wakeup_time, gym_time = commitment
        print(f"[scheduler] Found commitment for {tomorrow_str}: wake={wakeup_time}, gym={gym_time}")

        # Schedule wake-up job (skip if NONE)
        if wakeup_time and wakeup_time.upper() != "NONE":
            print(f"[scheduler] Parsing wake-up time: '{wakeup_time}' with base_date={tomorrow}")
            wakeup_dt = _parse_time_to_datetime(wakeup_time, tomorrow)
            if wakeup_dt:
                print(f"[scheduler] Parsed wake-up datetime: {wakeup_dt.isoformat()}")
                # Remove existing wake-up job if present
                try:
                    scheduler.remove_job(_wakeup_job_id)
                    print(f"[scheduler] Removed existing wake-up job")
                except:
                    pass

                # Ensure the wake-up time is in the future
                now = timezone.now_local()
                print(f"[scheduler] Current time: {now.isoformat()}, Wake-up time: {wakeup_dt.isoformat()}")
                if wakeup_dt <= now:
                    # Wake-up time has already passed for today, schedule for next day
                    print(f"[scheduler] Wake-up time {wakeup_dt} has passed. Scheduling for next day instead.")
                    wakeup_dt = wakeup_dt + timedelta(days=1)
                    print(f"[scheduler] Adjusted wake-up time to: {wakeup_dt.isoformat()}")

                print(f"[scheduler] Adding job with DateTrigger for {wakeup_dt.isoformat()}")
                scheduler.add_job(
                    scheduled_wakeup,
                    trigger=DateTrigger(run_date=wakeup_dt),
                    id=_wakeup_job_id,
                    name="Dynamic Wake-up",
                    replace_existing=True
                )
                print(f"[scheduler] Scheduled wake-up for {wakeup_dt.isoformat()}")
            else:
                print(f"[scheduler] ERROR: Could not parse wake-up time '{wakeup_time}'")
        else:
            # Remove wake-up job if exists (rest day)
            print(f"[scheduler] No wake-up scheduled (wakeup_time={wakeup_time})")
            try:
                scheduler.remove_job(_wakeup_job_id)
                print("[scheduler] Removed existing wake-up job (rest day)")
            except:
                pass

        # Schedule gym check-in job (gym_time + 120 min), skip if REST
        if gym_time and gym_time.upper() not in ("REST", "NONE"):
            gym_dt = _parse_time_to_datetime(gym_time, tomorrow)
            if gym_dt:
                checkin_dt = gym_dt + timedelta(minutes=120)

                # Remove existing gym check-in job if present
                try:
                    scheduler.remove_job(_gym_checkin_job_id)
                    print(f"[scheduler] Removed existing gym check-in job")
                except:
                    pass

                # Ensure the check-in time is in the future
                now = timezone.now_local()
                if checkin_dt <= now:
                    # Gym time has already passed, schedule for next day
                    print(f"[scheduler] Gym check-in time {checkin_dt} has passed. Scheduling for next day instead.")
                    checkin_dt = checkin_dt + timedelta(days=1)

                scheduler.add_job(
                    scheduled_gym_checkin,
                    trigger=DateTrigger(run_date=checkin_dt),
                    id=_gym_checkin_job_id,
                    name="Dynamic Gym Check-in",
                    replace_existing=True
                )
                print(f"[scheduler] Scheduled gym check-in for {checkin_dt.isoformat()}")
            else:
                print(f"[scheduler] ERROR: Could not parse gym time '{gym_time}'")
        else:
            # Remove gym check-in job if exists (rest day)
            try:
                scheduler.remove_job(_gym_checkin_job_id)
                print("[scheduler] No gym check-in scheduled (rest day)")
            except:
                pass

    except Exception as e:
        print(f"[scheduler] Error scheduling dynamic jobs: {e}")
        import traceback
        traceback.print_exc()


async def schedule_tomorrow_jobs():
    """Job that runs each evening to schedule tomorrow's wake-up and gym check-in."""
    print(f"[scheduler] Scheduling tomorrow's jobs at {timezone.now_local().isoformat()}")
    schedule_dynamic_jobs()

async def send_weekly_report():
    """Generate and send weekly report via Telegram."""
    print(f"[scheduler] Sending weekly report at {timezone.now_local().isoformat()}")
    try:
        report = coach.generate_weekly_report()
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=report)
        print("[scheduler] Weekly report sent successfully")
    except Exception as e:
        print(f"[scheduler] Error sending weekly report: {e}")

async def check_and_apply_penalty():
    """Check goal compliance and trigger penalty if goals missed."""
    print(f"[scheduler] Checking goal compliance at {timezone.now_local().isoformat()}")
    try:
        # Check if Jocko is paused due to insufficient funds
        if database.get_setting("jocko_paused") == "1":
            reason = database.get_setting("jocko_paused_reason") or ""
            print(f"[scheduler] Jocko is paused ({reason}) - skipping penalty check")
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f"⏸️ **Penalty check skipped - Jocko is paused**\n\n"
                     f"Reason: {reason.replace('_', ' ').title()}\n"
                     f"Use /revive to resume once funds are added.",
                parse_mode="Markdown"
            )
            return

        # Check if Jocko is active
        is_active = database.get_setting("jocko_active") == "1"
        penalty_start = database.get_setting("penalty_start_date")
        week_start = coach._get_week_start(0)

        # If not active, skip penalty
        if not is_active:
            print("[scheduler] Jocko is deactivated - skipping penalty check")
            return

        # If penalty_start_date is set and we're before that date, skip
        if penalty_start and week_start[:10] < penalty_start:
            print(f"[scheduler] Penalty period hasn't started yet (starts {penalty_start}) - skipping")
            return

        # Get compliance check
        compliance = coach.check_goal_compliance()

        if compliance["all_met"]:
            print("[scheduler] All goals met - no penalty applied")
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text="✅ GOALS MET! No penalty this week. Good work."
            )
            return

        # Goals missed - apply penalty
        penalty_amount = float(database.get_setting("penalty_amount") or 1)
        recipient = database.get_setting("recipient_email") or PAYPAL_RECIPIENT_EMAIL

        print(f"[scheduler] Goals missed - applying ${penalty_amount} penalty to {recipient}")

        # Send penalty via PayPal
        result = payments.send_penalty(
            amount=penalty_amount,
            recipient_email=recipient,
            week_start=week_start
        )

        # Check if penalty failed due to insufficient funds - pause the bot
        if not result["success"] and result.get("insufficient_funds"):
            balance = result.get("balance")
            shortfall = result.get("shortfall", penalty_amount)

            print(f"[scheduler] INSUFFICIENT FUNDS during penalty - pausing bot. Balance=${balance}, Required=${penalty_amount}")

            # Pause the bot
            database.set_setting("jocko_paused", "1")
            database.set_setting("jocko_paused_reason", "insufficient_funds")
            database.set_setting("jocko_paused_at", timezone.now_local().isoformat())

            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=f"🚨 **INSUFFICIENT FUNDS - BOT PAUSED**\n\n"
                     f"PayPal Balance: ${balance:.2f if balance else 'N/A'} AUD\n"
                     f"Required: ${penalty_amount:.2f} AUD\n"
                     f"Shortfall: ${shortfall:.2f} AUD\n\n"
                     f"⏸️ **All wake-ups, gym check-ins, and penalties are now PAUSED.**\n\n"
                     f"Add funds to your PayPal account, then use /revive to resume.",
                parse_mode="Markdown"
            )
            return

        # Log the penalty
        database.log_penalty(
            week_start=week_start,
            goal_workouts=compliance["goals"]["workouts_per_week"],
            actual_workouts=compliance["current"]["session_count"],
            goal_sprints=compliance["goals"]["sprints_per_week"],
            actual_sprints=compliance["current"]["sprint_count"],
            penalty_amount=penalty_amount,
            paid=1 if result["success"] else 0,
            recipient_email=recipient
        )

        # Notify user
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        if result["success"]:
            missed = []
            if not compliance["workouts_met"]:
                missed.append(f"workouts ({compliance['current']['session_count']}/{compliance['goals']['workouts_per_week']})")
            if not compliance["sprints_met"]:
                missed.append(f"sprints ({compliance['current']['session_count']}/{compliance['goals']['sprints_per_week']})")

            message = (
                f"❌ GOALS MISSED: {', '.join(missed)}\n\n"
                f"Penalty of ${penalty_amount} AUD sent to {recipient}.\n"
                f"Payout ID: {result.get('payout_batch_id', 'N/A')}\n\n"
                f"Step it up next week."
            )
        else:
            message = (
                f"❌ GOALS MISSED - but penalty payout failed!\n"
                f"Error: {result.get('error', 'Unknown error')}\n\n"
                f"Manual payment may be required."
            )

        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print(f"[scheduler] Penalty process complete: {result}")

    except Exception as e:
        print(f"[scheduler] Error in penalty check: {e}")

def _generate_proactive_message(context_type, intensity, extra_context=None):
    """
    Generate an AI-powered proactive message based on context and intensity.
    
    context_type: evening_commitment, morning_check_in, midday_nudge, evening_warning, 
                  breach_alert, sunday_planning
    intensity: 1-10
    extra_context: dict with additional data for the prompt
    """
    from openai import OpenAI
    from config import OPENAI_API_KEY, OPENAI_MODEL
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Build context-specific instruction
    context_instructions = {
        "evening_commitment": (
            "Ask the user for tomorrow's wake-up time and gym time. "
            "Request they reply with format: WAKE: [time], GYM: [time]. "
            "Be direct but natural. Vary your phrasing - never use the same opening twice."
        ),
        "morning_check_in": (
            "Send a morning check-in message. Ask about today's training plan. "
            "Reference their current progress if relevant. Be motivating but authentic."
        ),
        "midday_nudge": (
            "Send a midday nudge - no session logged yet today. "
            "Ask when they're training. Be appropriately pushy based on intensity."
        ),
        "evening_warning": (
            "Send an evening warning - no session today and goals are at risk. "
            "Point out the gap between commitment and action. Be direct."
        ),
        "breach_alert": (
            "Alert the user that their weekly goal is now mathematically impossible. "
            "Be clear about the consequences. Don't sugarcoat it."
        ),
        "sunday_planning": (
            "Ask about the upcoming week's training schedule. "
            "Get them to commit to specific days. Set the tone for the week."
        )
    }
    
    instruction = context_instructions.get(context_type, "Send a coaching message.")

    # Build extra context string
    context_str = ""
    if extra_context:
        for key, value in extra_context.items():
            context_str += f"\n{key}: {value}"

    # Check grace period status
    import coach
    week_start = coach._get_week_start(0)
    is_active = database.get_setting("jocko_active") == "1"
    penalty_start = database.get_setting("penalty_start_date")
    grace_context = ""
    if not is_active:
        grace_context = "\nNote: Jocko is currently deactivated. No penalties will be applied."
    elif penalty_start and week_start[:10] < penalty_start:
        grace_context = f"\nNote: This is a grace period week. Penalties start on {penalty_start}. Use this time to establish the routine."

    system_prompt = f"""You are a personal accountability and fitness coach. Your intensity level is {intensity}/10.
You take on the character of Jocko Willink, embodying his discipline and intensity.
At intensity 1-3 you are warm, kind and encouraging. At 4-6 you are direct and no-nonsense.
At 7-9 you are aggressive and confrontational. At 10 you are full David Goggins — brutal and relentless.

RULES:
- You MUST use EXACTLY 2 sentences. No more, no less.
- Count your sentences: First sentence. Second sentence. Done.
- If you write more than 2 sentences, you have failed.
- Vary your phrasing naturally each time.
- Speak like a real person would. Be concise but authentic."""

    user_prompt = f"""Your task: {instruction}{context_str}{grace_context}

REMEMBER: EXACTLY 2 SENTENCES. Count them."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    message = response.choices[0].message.content.strip()
    return message

async def evening_commitment_prompt():
    """Evening commitment prompt - asks for wake-up and gym time. Fires daily at 8:00 PM.
    Skips if tomorrow's commitment is already recorded."""
    try:
        # Check if Jocko is dormant or deactivated
        if database.get_setting("jocko_dormant") == "1":
            print("[scheduler] Jocko is dormant - skipping evening commitment prompt")
            return
        if database.get_setting("jocko_active") != "1":
            print("[scheduler] Jocko is deactivated - skipping evening commitment prompt")
            return

        frequency = int(database.get_setting("frequency") or 5)
        if frequency < 1:
            return

        # Check if tomorrow's commitment already exists
        tomorrow = timezone.now_local().date() + timedelta(days=1)
        tomorrow_str = tomorrow.isoformat()
        existing_commitment = database.get_daily_commitment(tomorrow_str)

        if existing_commitment and (existing_commitment[0] or existing_commitment[1]):
            print(f"[scheduler] Tomorrow's commitment already recorded ({tomorrow_str}: wake={existing_commitment[0]}, gym={existing_commitment[1]}) - skipping prompt")
            return

        print(f"[scheduler] Evening commitment prompt at {timezone.now_local().isoformat()}")
        intensity = int(database.get_setting("intensity") or 5)

        message = _generate_proactive_message("evening_commitment", intensity)

        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("[scheduler] Evening commitment prompt sent")
    except Exception as e:
        print(f"[scheduler] Error in evening commitment prompt: {e}")

async def morning_check_in():
    """Morning check-in message. Fires daily if frequency >= 1."""
    try:
        # Check if Jocko is dormant or deactivated
        if database.get_setting("jocko_dormant") == "1":
            print("[scheduler] Jocko is dormant - skipping morning check-in")
            return
        if database.get_setting("jocko_active") != "1":
            print("[scheduler] Jocko is deactivated - skipping morning check-in")
            return
        frequency = int(database.get_setting("frequency") or 5)
        if frequency < 1:
            return
        
        print(f"[scheduler] Morning check-in at {timezone.now_local().isoformat()}")
        intensity = int(database.get_setting("intensity") or 5)
        
        # Get current status for context
        this_week = coach._get_week_start(0)
        current = coach._calculate_summary(this_week)
        compliance = coach.check_goal_compliance()
        
        extra_context = {
            "Workouts this week": f"{current.get('session_count', 0)}/{compliance['goals']['workouts_per_week']}",
            "Sprints this week": f"{current.get('sprint_count', 0)}/{compliance['goals']['sprints_per_week']}"
        }
        
        message = _generate_proactive_message("morning_check_in", intensity, extra_context)
        
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("[scheduler] Morning check-in sent")
    except Exception as e:
        print(f"[scheduler] Error in morning check-in: {e}")

async def midday_nudge():
    """Midday nudge if no session logged. Fires if frequency >= 7."""
    try:
        # Check if Jocko is dormant or deactivated
        if database.get_setting("jocko_dormant") == "1":
            print("[scheduler] Jocko is dormant - skipping midday nudge")
            return
        if database.get_setting("jocko_active") != "1":
            print("[scheduler] Jocko is deactivated - skipping midday nudge")
            return

        frequency = int(database.get_setting("frequency") or 5)
        if frequency < 7:
            return

        # Check if session already logged today
        today_local = timezone.now_local()
        today_start = timezone.to_utc(today_local.replace(hour=0, minute=0, second=0, microsecond=0)).isoformat()
        tomorrow_start = timezone.to_utc((today_local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)).isoformat()
        todays_activities = database.get_activities_between(today_start, tomorrow_start)

        if todays_activities:
            print("[scheduler] Midday nudge skipped - session already logged today")
            return

        # Check if today was a committed rest day
        today_str = today_local.date().isoformat()
        commitment = database.get_daily_commitment(today_str)
        if commitment and commitment[1] and commitment[1].upper() in ("REST", "NONE"):
            print("[scheduler] Midday nudge skipped - today was a committed rest day")
            return

        print(f"[scheduler] Midday nudge at {timezone.now_local().isoformat()}")
        intensity = int(database.get_setting("intensity") or 5)

        message = _generate_proactive_message("midday_nudge", intensity)

        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("[scheduler] Midday nudge sent")
    except Exception as e:
        print(f"[scheduler] Error in midday nudge: {e}")

async def evening_warning():
    """Evening warning if no session and goal at risk. Fires if frequency >= 4."""
    try:
        # Check if Jocko is dormant
        if database.get_setting("jocko_dormant") == "1":
            print("[scheduler] Jocko is dormant - skipping evening warning")
            return
        if database.get_setting("jocko_active") != "1":
            print("[scheduler] Jocko is deactivated - skipping evening warning")
            return

        frequency = int(database.get_setting("frequency") or 5)
        if frequency < 4:
            return

        # Check if session already logged today
        today_local = timezone.now_local()
        today_start = timezone.to_utc(today_local.replace(hour=0, minute=0, second=0, microsecond=0)).isoformat()
        tomorrow_start = timezone.to_utc((today_local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)).isoformat()
        todays_activities = database.get_activities_between(today_start, tomorrow_start)

        if todays_activities:
            print("[scheduler] Evening warning skipped - session already logged today")
            return

        # Check if today was a committed rest day
        today_str = today_local.date().isoformat()
        commitment = database.get_daily_commitment(today_str)
        if commitment and commitment[1] and commitment[1].upper() in ("REST", "NONE"):
            print("[scheduler] Evening warning skipped - today was a committed rest day")
            return
            return

        # Check if goal is at risk (not just unmet, but actually at risk given days remaining)
        compliance = coach.check_goal_compliance()
        workouts_done = compliance['current']['session_count']
        workouts_goal = compliance['goals']['workouts_per_week']
        days_left = 7 - timezone.now_local().date().weekday() - 1  # Days remaining in week (0 on Sunday)

        # Calculate minimum workouts needed to stay on track
        # If we have X days left and need Y more workouts, we need at least Y days to do them
        workouts_needed = workouts_goal - workouts_done

        # Only warn if:
        # 1. Goals are not met AND
        # 2. We're behind schedule (workouts_needed > days_left) OR it's the weekend and nothing done
        is_behind = workouts_needed > days_left
        is_weekend = timezone.now_local().date().weekday() >= 5  # Saturday=5, Sunday=6
        weekend_concern = is_weekend and workouts_done < workouts_goal and workouts_done == 0

        if compliance['all_met'] or (not is_behind and not weekend_concern):
            print(f"[scheduler] Evening warning skipped - on track ({workouts_done}/{workouts_goal}, {days_left} days left)")
            return

        print(f"[scheduler] Evening warning at {timezone.now_local().isoformat()}")
        intensity = int(database.get_setting("intensity") or 5)

        extra_context = {
            "Current progress": f"{workouts_done}/{workouts_goal} workouts",
            "Days remaining": days_left
        }

        message = _generate_proactive_message("evening_warning", intensity, extra_context)

        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("[scheduler] Evening warning sent")
    except Exception as e:
        print(f"[scheduler] Error in evening warning: {e}")


async def breach_alert():
    """Breach alert if goal mathematically impossible. Fires if frequency >= 4."""
    try:
        # Check if Jocko is dormant or deactivated
        if database.get_setting("jocko_dormant") == "1":
            print("[scheduler] Jocko is dormant - skipping breach alert")
            return
        if database.get_setting("jocko_active") != "1":
            print("[scheduler] Jocko is deactivated - skipping breach alert")
            return

        frequency = int(database.get_setting("frequency") or 5)
        if frequency < 4:
            return

        # Check if goal is mathematically impossible
        compliance = coach.check_goal_compliance()
        if compliance['all_met']:
            return

        workouts_done = compliance['current']['session_count']
        workouts_goal = compliance['goals']['workouts_per_week']
        days_left = 7 - timezone.now_local().date().weekday() - 1

        # Check if mathematically impossible
        if workouts_done + days_left < workouts_goal:
            print(f"[scheduler] Breach alert at {timezone.now_local().isoformat()}")
            intensity = int(database.get_setting("intensity") or 5)

            extra_context = {
                "Current progress": f"{workouts_done}/{workouts_goal} workouts",
                "Days remaining": days_left,
                "Status": "Goal is mathematically impossible"
            }

            message = _generate_proactive_message("breach_alert", intensity, extra_context)

            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            print("[scheduler] Breach alert sent")
    except Exception as e:
        print(f"[scheduler] Error in breach alert: {e}")

async def sunday_preweek_planning():
    """Sunday pre-week planning prompt. Fires Sunday evening if frequency >= 1."""
    try:
        # Check if Jocko is dormant or deactivated
        if database.get_setting("jocko_dormant") == "1":
            print("[scheduler] Jocko is dormant - skipping Sunday pre-week planning")
            return
        if database.get_setting("jocko_active") != "1":
            print("[scheduler] Jocko is deactivated - skipping Sunday pre-week planning")
            return

        frequency = int(database.get_setting("frequency") or 5)
        if frequency < 1:
            return

        print(f"[scheduler] Sunday pre-week planning at {timezone.now_local().isoformat()}")
        intensity = int(database.get_setting("intensity") or 5)
        
        message = _generate_proactive_message("sunday_planning", intensity)
        
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("[scheduler] Sunday pre-week planning sent")
    except Exception as e:
        print(f"[scheduler] Error in Sunday pre-week planning: {e}")

async def _should_run_job(min_frequency):
    """Check if job should run based on current frequency setting."""
    frequency = int(database.get_setting("frequency") or 5)
    return frequency >= min_frequency

def start_scheduler():
    """Start the APScheduler with all proactive prompting jobs."""
    global scheduler
    scheduler = AsyncIOScheduler()
    
    # Weekly report: Sunday at 8 PM
    scheduler.add_job(
        send_weekly_report,
        trigger=CronTrigger(day_of_week="sun", hour=20, minute=0),
        id="weekly_report",
        name="Weekly Report",
        replace_existing=True
    )
    
    # Penalty check: Sunday at 11:59 PM (end of week)
    scheduler.add_job(
        check_and_apply_penalty,
        trigger=CronTrigger(day_of_week="sun", hour=23, minute=59),
        id="penalty_check",
        name="Penalty Check",
        replace_existing=True
    )
    
    # Phase 6: Proactive prompting jobs
    # REMOVED: Static morning_check_in replaced by Phase 7 dynamic wake-up system

    # Phase 7: Dynamic job scheduler - runs at 9 PM to schedule tomorrow's wake-up and gym check-in
    scheduler.add_job(
        schedule_tomorrow_jobs,
        trigger=CronTrigger(hour=21, minute=0),
        id="schedule_tomorrow_jobs",
        name="Schedule Tomorrow's Jobs",
        replace_existing=True
    )

    # Note: Dynamic jobs are scheduled after scheduler.start() to ensure
    # jobs can be properly added to the running scheduler (see end of start_scheduler())

    # Midday nudge: daily at 12:00 PM (frequency >= 7)
    scheduler.add_job(
        midday_nudge,
        trigger=CronTrigger(hour=12, minute=0),
        id="midday_nudge",
        name="Midday Nudge",
        replace_existing=True
    )
    
    # Evening warning: daily at 6:00 PM (frequency >= 4)
    scheduler.add_job(
        evening_warning,
        trigger=CronTrigger(hour=18, minute=0),
        id="evening_warning",
        name="Evening Warning",
        replace_existing=True
    )
    
    # Breach alert: daily at 8:00 PM (frequency >= 4)
    scheduler.add_job(
        breach_alert,
        trigger=CronTrigger(hour=20, minute=0),
        id="breach_alert",
        name="Breach Alert",
        replace_existing=True
    )
    
    # Sunday pre-week planning: Sunday at 7:00 PM (frequency >= 1)
    scheduler.add_job(
        sunday_preweek_planning,
        trigger=CronTrigger(day_of_week="sun", hour=19, minute=0),
        id="sunday_preweek_planning",
        name="Sunday Pre-week Planning",
        replace_existing=True
    )
    
    # Evening commitment prompt: daily at 8:00 PM (frequency >= 1)
    scheduler.add_job(
        evening_commitment_prompt,
        trigger=CronTrigger(hour=20, minute=0),
        id="evening_commitment_prompt",
        name="Evening Commitment Prompt",
        replace_existing=True
    )

    scheduler.start()
    print("[scheduler] Scheduler started with Phase 7 dynamic wake-up system.")
    print("[scheduler] Jobs: Weekly report (Sun 8PM), Penalty check (Sun 11:59PM), Evening commitment (daily 8PM), Schedule tomorrow (daily 9PM), Midday nudge (daily 12PM), Evening warning (daily 6PM), Breach alert (daily 8PM), Sunday planning (Sun 7PM)")

    # Schedule dynamic jobs AFTER scheduler is started
    schedule_dynamic_jobs()

    return scheduler

def stop_scheduler():
    """Stop the scheduler."""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        print("[scheduler] Scheduler stopped.")

def get_scheduler():
    """Get the current scheduler instance."""
    return scheduler