from datetime import datetime, timedelta
from openai import OpenAI
import database
import goals
from config import OPENAI_API_KEY, CONVERSATION_HISTORY_LIMIT, OPENAI_MODEL
import stoic
import timezone

client = OpenAI(api_key=OPENAI_API_KEY)

def _base_persona_prompt(intensity: int, extra_capabilities: str = "") -> str:
    """Return the base persona prompt shared across all coaching interactions."""
    return f"""You are Jocko Willink — a disciplined, no-nonsense accountability coach. You use his phrases like "Good!" and "get after it".
Your intensity level is {intensity}/10.
At intensity 1-3 you are warm, kind and encouraging. At 4-6 you are direct and no-nonsense.
At 7-9 you are aggressive and confrontational. At 10 you are full David Goggins — brutal and relentless.
Never break character. Vary your phrasing naturally.

YOU ARE AN AI COACH WITH FULL SYSTEM AWARENESS:
- You were built by your user and run on a Python system with a SQLite database
- You store: fitness activities, goals, all conversations, daily commitments, penalties, and settings
- You pull fitness data from Garmin Connect (activities, heart rate, body battery)
- You can send PayPal penalties when goals are missed
- You calculate fatigue scores, trends, and analyze training data

YOUR DAILY COMMITMENT SYSTEM — THIS IS YOUR CORE FUNCTION:
1. EVENING: You ask the user for their wake-up time and gym time for the next day
2. WAKE-UP: You send a wake-up message at their committed time with a Daily Stoic passage
3. GYM CHECK-IN: You check if they completed their gym session within the committed window
4. You remember their commitments and hold them accountable

YOU HAVE MEMORY:
- You can see conversation history and reference past exchanges
- You remember what the user told you in previous messages
- You track whether they kept their commitments or broke their word

{extra_capabilities}"""

def generate_wakeup_message(intensity: int) -> str:
    """Generate AI wake-up message with Stoic entry appended."""
    entry = stoic.get_daily_stoic_entry()

    system_prompt = _base_persona_prompt(intensity) + """

RULES:
- You MUST use EXACTLY 2 sentences. No more, no less.
- Count your sentences: First sentence. Second sentence. Done.
- If you write more than 2 sentences, you have failed.
- Be punchy and direct."""

    prompt = """Generate a wake-up message. It's time to get up and start the day. Be motivating but authentic.
Vary your phrasing naturally — never repeat the same opening twice.

REMEMBER: EXACTLY 2 SENTENCES. Count them."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )

    message = response.choices[0].message.content.strip()

    # Append Stoic entry and WAKE_UP trigger token
    stoic_text = f"\n\n📖 Daily Stoic: {entry['title']}\n\"{entry['quote']}\"\n— {entry['author']}\n\n💭 Reflection: {entry['reflection']}"
    message += stoic_text
    message += "\n\nWAKE_UP"

    return message

def generate_gym_checkin_message(intensity: int, session_found: bool) -> str:
    """Generate gym check-in message based on whether session was found."""
    system_prompt = _base_persona_prompt(intensity) + """

RULES:
- You MUST use EXACTLY 2 sentences. No more, no less.
- Count your sentences: First sentence. Second sentence. Done.
- If you write more than 2 sentences, you have failed."""

    if session_found:
        prompt = """The user has completed their gym session as committed. Acknowledge this with appropriate intensity.
At high intensity, this is approval for keeping their word. At low intensity, warm encouragement.

REMEMBER: EXACTLY 2 SENTENCES. Count them."""
    else:
        prompt = """The user MISSED their committed gym session. No activity found in the window.
At high intensity, this is a confrontation about broken commitment. At low intensity, concerned inquiry.

REMEMBER: EXACTLY 2 SENTENCES. Count them."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content.strip()

def check_gym_session_in_window(gym_time_str: str, window_minutes: int = 120) -> bool:
    """Check if a gym session exists within the window after gym_time."""
    try:
        # Get current time in local timezone
        now_local = timezone.now_local()
        today = now_local.date()

        # Handle various time formats (HH:MM, H:MM AM/PM)
        gym_time_str = gym_time_str.strip().upper()
        if 'AM' in gym_time_str or 'PM' in gym_time_str:
            gym_time = datetime.strptime(gym_time_str, "%I:%M %p").time()
        elif ':' in gym_time_str:
            gym_time = datetime.strptime(gym_time_str, "%H:%M").time()
        else:
            # Handle HHMM format
            gym_time = datetime.strptime(gym_time_str, "%H%M").time()

        # Create timezone-aware datetime for gym time
        gym_datetime = datetime.combine(today, gym_time).replace(tzinfo=timezone.get_user_timezone())
        window_end = gym_datetime + timedelta(minutes=window_minutes)

        # Get today's activities - query using UTC times
        today_start_utc = timezone.to_utc(datetime.combine(today, datetime.min.time()))
        tomorrow_start_utc = timezone.to_utc(datetime.combine(today + timedelta(days=1), datetime.min.time()))

        activities = database.get_activities_between(
            today_start_utc.isoformat(),
            tomorrow_start_utc.isoformat()
        )

        for activity in activities:
            # activity: (id, name, type, start_time, duration, distance, calories, avg_hr, max_hr, bb_start, bb_end)
            start_time_str = activity[3]
            try:
                # Parse UTC time and convert to local for comparison
                activity_start_utc = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                activity_start_local = timezone.to_local(activity_start_utc)

                if gym_datetime <= activity_start_local <= window_end:
                    return True
            except:
                continue

        return False
    except Exception as e:
        print(f"[coach] Error checking gym session: {e}")
        return False

def _get_week_start(offset=0):
    """Get start of week (Monday) in UTC ISO format for database queries."""
    now_local = timezone.now_local()
    today = now_local.date()
    monday = today - timedelta(days=today.weekday()) - timedelta(weeks=offset)
    # Convert to datetime at midnight in local timezone, then to UTC
    monday_local = datetime.combine(monday, datetime.min.time()).replace(tzinfo=timezone.get_user_timezone())
    monday_utc = timezone.to_utc(monday_local)
    return monday_utc.isoformat()

def _calculate_summary(week_start_str):
    activities = database.get_activities_since(week_start_str)
    total_distance = 0.0
    total_time     = 0.0
    total_calories = 0.0
    hr_readings    = []
    session_count  = 0
    sprint_count   = 0

    for row in activities:
        # id(0), name(1), type(2), start_time(3), duration(4), distance(5), calories(6), avg_hr(7), max_hr(8), body_battery_start(9), body_battery_end(10)
        _, name, activity_type, start_time, duration, distance, calories, avg_hr, _, _, _ = row
        if start_time >= week_start_str:
            session_count  += 1
            total_distance += distance or 0
            total_time     += duration or 0
            total_calories += calories or 0
            if avg_hr:
                hr_readings.append(avg_hr)
            if activity_type and "sprint" in activity_type.lower():
                sprint_count += 1

    avg_hr = round(sum(hr_readings) / len(hr_readings), 1) if hr_readings else None
    return {
        "session_count":  session_count,
        "sprint_count":   sprint_count,
        "total_distance": round(total_distance, 2),
        "total_time":     round(total_time, 1),
        "total_calories": round(total_calories),
        "avg_hr":         avg_hr,
    }

def _get_hr_trend():
    """Calculate HR trend over last 7 days vs previous 7 days."""
    now_local = timezone.now_local()
    today = now_local.date()
    recent_start_local = datetime.combine(today - timedelta(days=7), datetime.min.time()).replace(tzinfo=timezone.get_user_timezone())
    recent_end_local = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.get_user_timezone())
    previous_start_local = datetime.combine(today - timedelta(days=14), datetime.min.time()).replace(tzinfo=timezone.get_user_timezone())
    previous_end_local = recent_start_local

    recent_start_utc = timezone.to_utc(recent_start_local).isoformat()
    recent_end_utc = timezone.to_utc(recent_end_local).isoformat()
    previous_start_utc = timezone.to_utc(previous_start_local).isoformat()
    previous_end_utc = timezone.to_utc(previous_end_local).isoformat()

    recent_activities = database.get_activities_between(recent_start_utc, recent_end_utc)
    previous_activities = database.get_activities_between(previous_start_utc, previous_end_utc)

    # avg_hr is at index 7 in the activities table
    recent_hrs = [a[7] for a in recent_activities if a[7]]
    previous_hrs = [a[7] for a in previous_activities if a[7]]

    recent_avg = sum(recent_hrs) / len(recent_hrs) if recent_hrs else None
    previous_avg = sum(previous_hrs) / len(previous_hrs) if previous_hrs else None

    if recent_avg and previous_avg:
        return round(recent_avg - previous_avg, 1), round(recent_avg, 1)
    return None, recent_avg

def _calculate_fatigue_score():
    """
    Calculate fatigue score based on:
    - HR trend (elevated HR = fatigue)
    - Session density (sessions per day over last 7 days)
    - Body battery trend (if available)
    Returns score 0-100 (0 = fully recovered, 100 = highly fatigued)
    """
    now_local = timezone.now_local()
    today = now_local.date()
    week_ago_local = datetime.combine(today - timedelta(days=7), datetime.min.time()).replace(tzinfo=timezone.get_user_timezone())
    two_weeks_ago_local = datetime.combine(today - timedelta(days=14), datetime.min.time()).replace(tzinfo=timezone.get_user_timezone())
    today_local = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.get_user_timezone())

    week_ago_utc = timezone.to_utc(week_ago_local).isoformat()
    two_weeks_ago_utc = timezone.to_utc(two_weeks_ago_local).isoformat()
    today_utc = timezone.to_utc(today_local).isoformat()

    # Get recent activities
    recent_activities = database.get_activities_between(week_ago_utc, today_utc)
    previous_activities = database.get_activities_between(two_weeks_ago_utc, week_ago_utc)

    score = 0
    factors = []

    # HR trend component (0-40 points) - avg_hr is at index 7
    recent_hrs = [a[7] for a in recent_activities if a[7]]
    previous_hrs = [a[7] for a in previous_activities if a[7]]

    if recent_hrs and previous_hrs:
        recent_avg = sum(recent_hrs) / len(recent_hrs)
        previous_avg = sum(previous_hrs) / len(previous_hrs)
        hr_diff = recent_avg - previous_avg

        if hr_diff > 10:
            score += 40
            factors.append("significantly elevated HR")
        elif hr_diff > 5:
            score += 25
            factors.append("elevated HR")
        elif hr_diff > 2:
            score += 10
            factors.append("slightly elevated HR")
        elif hr_diff < -5:
            score -= 10
            factors.append("lower HR (good recovery)")

    # Session density component (0-35 points)
    recent_count = len(recent_activities)
    if recent_count >= 7:
        score += 35
        factors.append("high session density")
    elif recent_count >= 5:
        score += 20
        factors.append("moderate session density")
    elif recent_count >= 3:
        score += 10
        factors.append("light session density")

    # Body battery component (0-25 points)
    bb = database.get_latest_body_battery()
    if bb is not None:
        if bb < 25:
            score += 25
            factors.append("very low body battery")
        elif bb < 50:
            score += 15
            factors.append("low body battery")
        elif bb > 75:
            score -= 10
            factors.append("high body battery")

    score = max(0, min(100, score))
    return score, factors

def _get_distance_trend():
    """Calculate week-on-week distance trend as percentage."""
    this_week = _get_week_start(0)
    last_week = _get_week_start(1)

    current = _calculate_summary(this_week)
    previous = _calculate_summary(last_week)

    if previous["total_distance"] > 0:
        pct_change = ((current["total_distance"] - previous["total_distance"]) / previous["total_distance"]) * 100
        return round(pct_change, 1)
    elif current["total_distance"] > 0:
        return 100.0
    return 0.0

def _body_battery_line():
    bb = database.get_latest_body_battery()
    if bb is None:
        return None
    if bb >= 70:
        return f"Body battery: {bb}% — plenty in the tank."
    elif bb >= 40:
        return f"Body battery: {bb}% — moderate reserves, manageable."
    else:
        return f"Body battery: {bb}% — running low, recovery may be needed."

def _fatigue_line():
    score, factors = _calculate_fatigue_score()
    if score >= 70:
        return f"Fatigue: {score}/100 — HIGH. {', '.join(factors)}. Prioritize recovery."
    elif score >= 40:
        return f"Fatigue: {score}/100 — MODERATE. {', '.join(factors)}. Balance work and rest."
    else:
        return f"Fatigue: {score}/100 — LOW. {', '.join(factors) if factors else 'Good recovery state.'} Ready to push."

def _trend_line():
    distance_trend = _get_distance_trend()
    hr_delta, recent_hr = _get_hr_trend()

    lines = []
    if distance_trend > 0:
        lines.append(f"Distance trend: +{distance_trend}% vs last week")
    elif distance_trend < 0:
        lines.append(f"Distance trend: {distance_trend}% vs last week")
    else:
        lines.append("Distance trend: stable")

    if hr_delta is not None:
        if hr_delta > 0:
            lines.append(f"HR trend: +{hr_delta} bpm vs last week")
        elif hr_delta < 0:
            lines.append(f"HR trend: {hr_delta} bpm vs last week")
        else:
            lines.append("HR trend: stable")

    return " | ".join(lines)

def generate_weekly_report():
    this_week = _get_week_start(0)
    last_week = _get_week_start(1)

    current   = _calculate_summary(this_week)
    previous  = _calculate_summary(last_week)
    intensity = int(database.get_setting("intensity") or 5)

    session_trend = current["session_count"] - previous["session_count"]
    trend_str     = f"+{session_trend}" if session_trend >= 0 else str(session_trend)
    compliance    = goals.compliance(current)
    bb_line       = _body_battery_line()
    fatigue_line  = _fatigue_line()
    trend_line    = _trend_line()

    # Check if in grace period
    is_active = database.get_setting("jocko_active") == "1"
    penalty_start = database.get_setting("penalty_start_date")
    in_grace_period = False
    grace_note = ""
    if is_active and penalty_start and this_week[:10] < penalty_start:
        in_grace_period = True
        grace_note = f"GRACE PERIOD: Penalties start on {penalty_start}. Use this week to establish your routine."
    elif not is_active:
        grace_note = "Jocko is currently DEACTIVATED. Use /activate to enable penalties."

    prompt = _base_persona_prompt(intensity) + f"""
Deliver a weekly training report based on this data. Be extremely concise. No bullet points. Speak directly to the athlete.
MAXIMUM 3-4 SENTENCES. Be punchy and direct.
Use the fatigue score and trends to guide your coaching — push harder when fatigue is low and recovery is good,
back off when fatigue is high. Factor in body battery and HR trends in your assessment.
{grace_note}

{compliance}
Sessions vs last week: {trend_str}
{trend_line}
{fatigue_line}
{f"{bb_line}" if bb_line else ""}
Total time: {current['total_time']} min"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    message = response.choices[0].message.content.strip()
    return message

def get_status():
    this_week  = _get_week_start(0)
    current    = _calculate_summary(this_week)
    compliance = goals.compliance(current)
    bb_line    = _body_battery_line()
    fatigue_line = _fatigue_line()
    trend_line = _trend_line()

    # Check activation status
    is_active = database.get_setting("jocko_active") == "1"
    penalty_start = database.get_setting("penalty_start_date")
    status_extra = ""
    if not is_active:
        status_extra = "\n\n🔴 Jocko is DEACTIVATED - use /activate to enable"
    elif penalty_start and this_week[:10] < penalty_start:
        status_extra = f"\n\n🟡 GRACE PERIOD - Penalties start {penalty_start}"
    else:
        status_extra = "\n\n🟢 Jocko is ACTIVE - Penalties enabled"

    status = f"Week starting {this_week}\n{compliance}\n{trend_line}\n{fatigue_line}"
    if bb_line:
        status += f"\n{bb_line}"
    status += status_extra
    return status

def check_goal_compliance():
    this_week = _get_week_start(0)
    current   = _calculate_summary(this_week)
    return goals.check_compliance(current)

def chat(user_message):
    history    = database.get_recent_conversations(CONVERSATION_HISTORY_LIMIT)
    this_week  = _get_week_start(0)
    current    = _calculate_summary(this_week)
    intensity  = int(database.get_setting("intensity") or 5)
    compliance = goals.compliance(current)
    bb_line    = _body_battery_line()
    fatigue_line = _fatigue_line()
    trend_line = _trend_line()

    # Get today's Daily Stoic entry
    stoic_entry = stoic.get_todays_stoic()
    stoic_context = f"""
TODAY'S DAILY STOIC ENTRY:
Title: {stoic_entry['title']}
Quote: "{stoic_entry['quote']}"
Author: {stoic_entry['author']}
Reflection: {stoic_entry['reflection']}
"""

    # Check if in grace period
    is_active = database.get_setting("jocko_active") == "1"
    penalty_start = database.get_setting("penalty_start_date")
    in_grace_period = False
    if is_active and penalty_start and this_week[:10] < penalty_start:
        in_grace_period = True

    system_prompt = _base_persona_prompt(
        intensity,
        extra_capabilities=" You communicate via Telegram."
    ) + f"""
RULES:
- You MUST use EXACTLY 2 sentences. No more, no less.
- Count your sentences: First sentence. Second sentence. Done.
- If you write more than 2 sentences, you have failed.

Use body battery and fatigue score as coaching colour — if fatigue is high or body battery is low, factor in recovery;
if both are good, push harder. Use trends to assess whether the athlete is improving or regressing.
{"This is a GRACE PERIOD week - penalties are not yet active. Use this as onboarding time to establish the routine, but still push for discipline." if in_grace_period else ""}

Current training context:
{compliance}
{trend_line}
{fatigue_line}
{f"{bb_line}" if bb_line else ""}
Total time this week: {current['total_time']} min

{stoic_context}"""

    messages = [{"role": "system", "content": system_prompt}]
    for role, content in history:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages
    )

    reply = response.choices[0].message.content.strip()
    database.save_conversation("user", user_message)
    database.save_conversation("assistant", reply)
    return reply