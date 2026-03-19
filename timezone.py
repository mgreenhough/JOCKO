"""Timezone utilities for Jocko AI Coach.

All times stored in UTC, converted to local timezone for display and scheduling.
Uses Garmin-derived timezone with config fallback.
"""

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, available_timezones
from typing import Optional
import database
from config import USER_TIMEZONE


def get_user_timezone() -> ZoneInfo:
    """Get user's timezone - from database if set, else config fallback."""
    tz_name = database.get_setting("timezone")
    if tz_name:
        return ZoneInfo(tz_name)
    return ZoneInfo(USER_TIMEZONE)


def set_user_timezone(tz_name: str) -> bool:
    """Set user's timezone in database. Returns True if valid timezone."""
    if tz_name in available_timezones():
        database.set_setting("timezone", tz_name)
        return True
    return False


def derive_timezone_from_garmin(local_time_str: str, gmt_time_str: str) -> Optional[str]:
    """Derive IANA timezone name from Garmin activity times.
    
    Args:
        local_time_str: ISO format local time (e.g., "2026-03-19T18:30:00")
        gmt_time_str: ISO format GMT/UTC time (e.g., "2026-03-19T08:30:00")
    
    Returns:
        IANA timezone name or None if derivation fails
    """
    try:
        # Parse times (naive, treat as UTC for calculation)
        local = datetime.fromisoformat(local_time_str.replace('Z', '+00:00'))
        gmt = datetime.fromisoformat(gmt_time_str.replace('Z', '+00:00'))
        
        # Calculate offset in hours
        offset_hours = int((local - gmt).total_seconds() / 3600)
        
        # Map offset to common IANA timezones
        # This is a simplified mapping - for production, consider more sophisticated detection
        offset_map = {
            -12: "Pacific/Auckland",  # NZDT during daylight saving
            -11: "Pacific/Auckland",
            -10: "Australia/Sydney",  # AEDT during daylight saving
            -9: "Australia/Sydney",
            -8: "Australia/Brisbane",  # AEST
            -7: "Asia/Tokyo",
            -6: "Asia/Shanghai",
            -5: "Asia/Shanghai",
            0: "UTC",
            5: "America/New_York",
            6: "America/Chicago",
            7: "America/Denver",
            8: "America/Los_Angeles",
            9: "America/Anchorage",
            10: "Pacific/Honolulu",
        }
        
        # Try to get stored timezone first to maintain consistency
        stored_tz = database.get_setting("timezone")
        if stored_tz:
            # Verify the stored timezone matches the offset
            try:
                tz = ZoneInfo(stored_tz)
                now = datetime.now(tz)
                current_offset = int(now.utcoffset().total_seconds() / 3600)
                if current_offset == offset_hours:
                    return stored_tz
            except:
                pass
        
        # Return mapped timezone or fallback to config
        return offset_map.get(offset_hours, USER_TIMEZONE)
    except Exception as e:
        print(f"Error deriving timezone: {e}")
        return None


def parse_garmin_time(time_str: str) -> datetime:
    """Parse Garmin time string to timezone-aware UTC datetime.
    
    Garmin provides times like "2026-03-19T08:30:00.0" (GMT/UTC)
    """
    # Handle various formats
    time_str = time_str.replace('Z', '+00:00')
    if '.' in time_str and '+' not in time_str and '-' not in time_str[10:]:
        # Has milliseconds but no timezone
        time_str = time_str.split('.')[0] + '+00:00'
    elif '+' not in time_str and '-' not in time_str[10:]:
        # No timezone info, assume UTC
        time_str = time_str + '+00:00'
    
    return datetime.fromisoformat(time_str)


def to_utc(dt: datetime) -> datetime:
    """Convert any datetime to UTC."""
    if dt.tzinfo is None:
        # Naive datetime - assume it's in user timezone
        dt = dt.replace(tzinfo=get_user_timezone())
    return dt.astimezone(timezone.utc)


def to_local(dt: datetime) -> datetime:
    """Convert UTC datetime to user local time."""
    if dt.tzinfo is None:
        # Assume UTC if naive
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_user_timezone())


def format_local(dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Format datetime in user's local timezone."""
    return to_local(dt).strftime(fmt)


def format_utc(dt: datetime, fmt: str = "%Y-%m-%dT%H:%M:%S+00:00") -> str:
    """Format datetime in UTC for storage."""
    return to_utc(dt).strftime(fmt)


def now_local() -> datetime:
    """Get current time in user's local timezone."""
    return datetime.now(get_user_timezone())


def now_utc() -> datetime:
    """Get current time in UTC."""
    return datetime.now(timezone.utc)


def get_start_of_week_local(dt: Optional[datetime] = None) -> datetime:
    """Get start of week (Monday) in local timezone."""
    if dt is None:
        dt = now_local()
    # Monday is 0, Sunday is 6
    days_since_monday = dt.weekday()
    start = dt - timedelta(days=days_since_monday)
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def get_start_of_day_local(dt: Optional[datetime] = None) -> datetime:
    """Get start of day in local timezone."""
    if dt is None:
        dt = now_local()
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def list_common_timezones() -> list:
    """List common timezone names for user selection."""
    common = [
        "Australia/Sydney",
        "Australia/Melbourne", 
        "Australia/Brisbane",
        "Australia/Perth",
        "Pacific/Auckland",
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "Europe/London",
        "Europe/Paris",
        "Asia/Tokyo",
        "Asia/Shanghai",
        "UTC",
    ]
    return common


def update_timezone_from_garmin_activity(activity: dict) -> Optional[str]:
    """Update timezone setting from a Garmin activity.
    
    Args:
        activity: Garmin activity dict with startTimeLocal and startTimeGMT
    
    Returns:
        Timezone name that was set, or None if failed
    """
    local_time = activity.get('startTimeLocal')
    gmt_time = activity.get('startTimeGMT')
    
    if not local_time or not gmt_time:
        return None
    
    tz_name = derive_timezone_from_garmin(local_time, gmt_time)
    if tz_name:
        database.set_setting("timezone", tz_name)
        print(f"Updated timezone to {tz_name} from Garmin activity")
    
    return tz_name
