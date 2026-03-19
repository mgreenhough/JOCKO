import logging
import asyncio
import re
import subprocess
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import database
import coach
import garmin
import goals
import scheduler
import config
import timezone
from config import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO)

def parse_commitment(message_text):
    """
    Parse commitment message for WAKE and GYM times.
    Returns (wakeup_time, gym_time) or (None, None) if not a commitment.
    Supports NONE for no wake-up alarm and REST for no gym session.

    Expected formats:
    - WAKE: 0500, GYM: 0600
    - WAKE 0530 GYM 0700
    - wake 5am gym 6am
    - WAKE: none, GYM: rest
    - wake none gym rest
    """
    text = message_text.upper().strip()

    # Check if this looks like a commitment message
    if 'WAKE' not in text and 'GYM' not in text:
        return None, None

    # Extract WAKE time or NONE
    # Use a more flexible pattern to capture time values including colons and AM/PM
    wake_match = re.search(r'WAKE[:\s]*(\S+(?:\s*[AP]M)?)', text, re.IGNORECASE)
    gym_match = re.search(r'GYM[:\s]*(\S+(?:\s*[AP]M)?)', text, re.IGNORECASE)

    wakeup_time = None
    gym_time = None

    if wake_match:
        val = wake_match.group(1)
        # Check for NONE keyword
        if val.upper() in ('NONE', 'NO'):
            wakeup_time = "NONE"
        else:
            # Try to parse as time
            time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(AM|PM)?', val, re.IGNORECASE)
            if time_match:
                hour = time_match.group(1)
                minute = time_match.group(2) or '00'
                ampm = time_match.group(3)
                wakeup_time = f"{hour.zfill(2)}:{minute}"
                if ampm:
                    wakeup_time += f" {ampm}"

    if gym_match:
        val = gym_match.group(1)
        # Check for REST/NONE keyword
        if val.upper() in ('REST', 'NONE', 'NO'):
            gym_time = "REST"
        else:
            # Try to parse as time
            time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(AM|PM)?', val, re.IGNORECASE)
            if time_match:
                hour = time_match.group(1)
                minute = time_match.group(2) or '00'
                ampm = time_match.group(3)
                gym_time = f"{hour.zfill(2)}:{minute}"
                if ampm:
                    gym_time += f" {ampm}"

    return wakeup_time, gym_time

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to your AI Accountability Coach! 💪\n\n"
        "Commands:\n"
        "/weekly - Generate weekly report\n"
        "/status - Check current status\n"
        "/goal [key] [value] - Set goals\n"
        "/intensity [1-10] - Set workout intensity\n"
        "/frequency [1-10] - Set workout frequency\n"
        "/penalty [amount] - Set penalty amount\n"
        "/recipient [email] - Set penalty recipient\n"
        "/pull - Pull latest Garmin data\n"
        "/update - Pull latest code from GitHub & restart\n"
        "/commands - Show all available commands\n"
        "/activate - Activate Jocko (penalties start next week)\n"
        "/deactivate - Deactivate Jocko (no penalties, still messages)\n"
        "/dormant - Put Jocko to sleep (completely silent)\n\n"
        "Or just send me a message to chat!"
    )

async def cmd_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display all available commands."""
    commands_text = """
📋 **Available Commands**

**Information:**
/weekly - Generate weekly training report
/status - Check current status and progress
/commands - Show this command list

**Goal Setting:**
/goal [key] [value] - Set goals (e.g., /goal workouts_per_week 5)
/intensity [1-10] - Set coaching intensity (1=gentle, 10=brutal)
/frequency [1-10] - Set check-in frequency (1=minimal, 10=constant)

**Penalty Settings:**
/penalty [amount] - Set penalty amount in AUD
/recipient [email] - Set penalty recipient email

**Data & Control:**
/pull - Pull latest Garmin data manually
/update - Pull latest code from GitHub & restart
/activate - Activate Jocko (penalties start next week or wake from dormant)
/deactivate - Deactivate penalties (messages still active)
/dormant - Put Jocko to sleep (completely silent)

**Daily Commitments:**
Simply message: "WAKE: 0600, GYM: 0700"
Use "WAKE: NONE, GYM: REST" for rest days

**Need help?** Just send a message to chat with Jocko!
"""
    await update.message.reply_text(commands_text, parse_mode="Markdown")

async def cmd_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Generating your weekly report...")
    report = coach.generate_weekly_report()
    await update.message.reply_text(report)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = coach.get_status()
    await update.message.reply_text(status)

async def cmd_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Current goals:\n" + goals.summary_text() + "\n\nUsage: /goal workouts_per_week 5")
        return
    key, val = args[0], args[1]
    if not val.replace(".", "").isdigit():
        await update.message.reply_text("Value must be a number.")
        return
    try:
        goals.set(key, float(val) if "." in val else int(val))
        await update.message.reply_text(f"{key} updated to {val}.")
    except ValueError as e:
        await update.message.reply_text(str(e))

async def cmd_intensity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or not args[0].isdigit() or not (1 <= int(args[0]) <= 10):
        await update.message.reply_text("Usage: /intensity 7  (1-10)")
        return
    database.set_setting("intensity", args[0])
    await update.message.reply_text(f"Intensity set to {args[0]}/10.")

async def cmd_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or not args[0].isdigit() or not (1 <= int(args[0]) <= 10):
        await update.message.reply_text("Usage: /frequency 5  (1-10)")
        return
    database.set_setting("frequency", args[0])
    await update.message.reply_text(f"Frequency set to {args[0]}/10.")

async def cmd_penalty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        amount = database.get_setting("penalty_amount")
        await update.message.reply_text(f"Current penalty: ${amount} AUD.")
        return
    if not args[0].replace(".", "").isdigit():
        await update.message.reply_text("Usage: /penalty 100")
        return
    # Update both database and config
    database.set_setting("penalty_amount", args[0])
    config.PENALTY_AMOUNT = args[0]
    await update.message.reply_text(f"Penalty amount updated to ${args[0]} AUD.")

async def cmd_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        email = database.get_setting("recipient_email")
        await update.message.reply_text(f"Current recipient: {email or 'not set'}.")
        return
    # Update both database and config
    database.set_setting("recipient_email", args[0])
    config.PAYPAL_RECIPIENT_EMAIL = args[0]
    await update.message.reply_text(f"Recipient updated to {args[0]}.")

async def cmd_pull(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Pulling Garmin data...")
    count = garmin.pull_activities()
    if count > 0:
        await update.message.reply_text(f"✅ Pulled {count} activities from Garmin.")
    else:
        await update.message.reply_text("⚠️ No activities pulled. Check logs for details or verify Garmin credentials.")


async def cmd_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pull latest code from GitHub and restart the service."""
    await update.message.reply_text("🔄 Updating from GitHub...")

    try:
        # Pull latest code
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd="/opt/coach",
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            await update.message.reply_text(f"❌ Git pull failed:\n{result.stderr}")
            return

        output = result.stdout.strip()
        await update.message.reply_text(f"✅ Git pull complete:\n```\n{output}\n```", parse_mode="Markdown")

        # Restart the service
        restart_result = subprocess.run(
            ["systemctl", "restart", "coach"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if restart_result.returncode != 0:
            await update.message.reply_text(f"⚠️ Code updated but restart failed:\n{restart_result.stderr}")
            return

        await update.message.reply_text("✅ Service restarted successfully. Update complete!")

    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ Update timed out. Check server manually.")
    except Exception as e:
        await update.message.reply_text(f"❌ Update failed: {str(e)}")

async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activate Jocko - penalties will start from next week."""
    database.set_setting("jocko_active", "1")

    # Calculate next Monday for penalty start
    from datetime import datetime, timedelta
    today = datetime.now().date()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7  # If today is Monday, start next Monday
    next_monday = today + timedelta(days=days_until_monday)

    database.set_setting("penalty_start_date", next_monday.isoformat())

    await update.message.reply_text(
        f"✅ **Jocko ACTIVATED**\n\n"
        f"Penalties will be enforced starting Monday ({next_monday}).\n"
        f"Current week is a grace period - use it to get on track!\n\n"
        f"Send your commitments each evening:\n"
        f"• WAKE: 0600, GYM: 0700\n"
        f"• WAKE: NONE, GYM: REST (for rest days)",
        parse_mode="Markdown"
    )

async def cmd_deactivate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deactivate Jocko - no penalties will be applied."""
    database.set_setting("jocko_active", "0")
    database.set_setting("penalty_start_date", "")
    await update.message.reply_text(
        "🔴 **Jocko DEACTIVATED**\n\n"
        "No penalties will be applied.\n"
        "Jocko will still send reminders and check-ins.\n"
        "Use /dormant to completely silence Jocko.\n"
        "Use /activate to restart when you're ready.",
        parse_mode="Markdown"
    )

async def cmd_dormant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Put Jocko in dormant mode - completely silent, no messages at all."""
    database.set_setting("jocko_active", "0")
    database.set_setting("jocko_dormant", "1")
    database.set_setting("penalty_start_date", "")
    await update.message.reply_text(
        "😴 **Jocko is now DORMANT**\n\n"
        "No messages, no reminders, no check-ins.\n"
        "Complete silence until you reactivate.\n\n"
        "Use /activate to wake Jocko up when you're ready.",
        parse_mode="Markdown"
    )

async def cmd_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View or update timezone setting."""
    args = context.args

    if not args:
        # Show current timezone
        current_tz = database.get_setting("timezone") or config.USER_TIMEZONE
        common_timezones = timezone.list_common_timezones()

        tz_list = "\n".join([f"  • {tz}" for tz in common_timezones])

        await update.message.reply_text(
            f"🌍 **Current Timezone:** `{current_tz}`\n\n"
            f"Timezone is automatically detected from Garmin activities.\n"
            f"You can manually set it with: `/timezone <timezone_name>`\n\n"
            f"Common timezones:\n{tz_list}\n\n"
            f"Or use any IANA timezone name (e.g., `Australia/Sydney`, `America/New_York`)",
            parse_mode="Markdown"
        )
        return

    # Set new timezone
    tz_name = args[0]
    if timezone.set_user_timezone(tz_name):
        await update.message.reply_text(
            f"✅ Timezone updated to `{tz_name}`.\n\n"
            f"All scheduling will now use this timezone.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ Invalid timezone: `{tz_name}`\n\n"
            f"Please use a valid IANA timezone name (e.g., `Australia/Sydney`, `America/New_York`)",
            parse_mode="Markdown"
        )

async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activate Jocko - penalties will start from next week."""
    database.set_setting("jocko_active", "1")
    database.set_setting("jocko_dormant", "0")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[main] Received message from chat_id: {update.effective_chat.id}")
    user_message = update.message.text
    print(f"[main] Message content: {user_message[:50]}...")

    try:
        # First, check if this is a commitment message
        wakeup_time, gym_time = parse_commitment(user_message)

        # Check if this is a valid commitment message (has WAKE or GYM keywords)
        text_upper = user_message.upper().strip()
        is_commitment = 'WAKE' in text_upper or 'GYM' in text_upper

        if is_commitment:
            # This is a commitment message - save it
            tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
            database.save_daily_commitment(tomorrow, wakeup_time, gym_time)

            # Acknowledge the commitment
            response_parts = []
            if wakeup_time == "NONE":
                response_parts.append("Wake-up: No alarm (rest)")
            elif wakeup_time:
                response_parts.append(f"Wake-up: {wakeup_time}")

            if gym_time == "REST":
                response_parts.append("Gym: Rest day")
            elif gym_time:
                response_parts.append(f"Gym: {gym_time}")

            reply = f"✅ LOCKED IN for tomorrow ({tomorrow}):\n" + "\n".join(response_parts)

            # Add intensity-based confirmation
            intensity = int(database.get_setting("intensity") or 5)

            # Special message for full rest day
            if wakeup_time == "NONE" and gym_time == "REST":
                reply += "\n\nFull rest day. Recover well."
            elif intensity >= 8:
                reply += "\n\nNo excuses. See you at wake-up."
            elif intensity >= 5:
                reply += "\n\nCommitted. I'll check in then."
            else:
                reply += "\n\nGreat! I'll remind you when it's time."

            await update.message.reply_text(reply)
            print(f"[main] Commitment saved: wake={wakeup_time}, gym={gym_time}")

            # Immediately reschedule jobs to ensure wake-up alarm is set
            # If it's after 9 PM, this schedules for tomorrow (the day after the commitment)
            # If it's before 9 PM, this schedules for the commitment day
            scheduler.schedule_dynamic_jobs()
            print("[main] Dynamic jobs rescheduled after commitment")

            return

        # Not a commitment - route to coach for normal chat
        reply = coach.chat(user_message)
        await update.message.reply_text(reply)
        print("[main] Reply sent successfully")
    except Exception as e:
        print(f"[main] Error handling message: {e}")
        await update.message.reply_text(f"Sorry, I encountered an error: {str(e)}")

def main():
    database.init_db()

    # Start the scheduler for automated jobs
    scheduler.start_scheduler()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("weekly",    cmd_weekly))
    app.add_handler(CommandHandler("status",    cmd_status))
    app.add_handler(CommandHandler("goal",      cmd_goal))
    app.add_handler(CommandHandler("intensity", cmd_intensity))
    app.add_handler(CommandHandler("activate",  cmd_activate))
    app.add_handler(CommandHandler("deactivate", cmd_deactivate))
    app.add_handler(CommandHandler("dormant", cmd_dormant))
    app.add_handler(CommandHandler("timezone", cmd_timezone))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("frequency", cmd_frequency))
    app.add_handler(CommandHandler("penalty",   cmd_penalty))
    app.add_handler(CommandHandler("recipient", cmd_recipient))
    app.add_handler(CommandHandler("pull",      cmd_pull))
    app.add_handler(CommandHandler("update",    cmd_update))
    app.add_handler(CommandHandler("commands",  cmd_commands))
    app.add_handler(CommandHandler("activate",  cmd_activate))
    app.add_handler(CommandHandler("deactivate", cmd_deactivate))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("[main] Bot running...")
    try:
        app.run_polling()
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop_scheduler()

if __name__ == "__main__":
    main()
