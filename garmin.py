from datetime import datetime, timedelta
from garminconnect import Garmin
from config import GARMIN_EMAIL, GARMIN_PASSWORD
import database

_client = None

def _get_client():
    global _client
    if _client is None:
        if not GARMIN_EMAIL or not GARMIN_PASSWORD:
            print("[garmin] No credentials provided.")
            return None
        try:
            print(f"[garmin] Attempting login with email: {GARMIN_EMAIL}")
            _client = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
            _client.login()
            print("[garmin] Logged in successfully.")
        except Exception as e:
            print(f"[garmin] Login failed: {e}")
            print(f"[garmin] Error type: {type(e).__name__}")
            return None
    return _client

def _map_activity_type(atype):
    """Map Garmin activity type to our simplified types."""
    atype_lower = atype.lower()
    if any(x in atype_lower for x in ["sprint", "run", "running"]):
        return "sprint"
    elif any(x in atype_lower for x in ["strength", "weight", "weights", "crossfit", "hiit"]):
        return "strength"
    elif any(x in atype_lower for x in ["cardio", "elliptical", "rowing", "indoor"]):
        return "cardio"
    else:
        return "other"

def pull_activities(days=14):
    client = _get_client()

    if not client:
        print("[garmin] No client available - not seeding dummy data automatically.")
        print("[garmin] Run /pull command manually to see detailed errors.")
        return 0

    try:
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()

        print(f"[garmin] Fetching activities from {start_date.date()} to {end_date.date()}")

        # Get activities in date range
        activities = client.get_activities_by_date(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )

        print(f"[garmin] Found {len(activities)} raw activities from Garmin")

        if not activities:
            print("[garmin] No activities found in date range.")
            return 0

        # Get body battery data if available
        try:
            body_battery_data = client.get_body_battery(start_date.strftime("%Y-%m-%d"))
            # Create a lookup dict by date
            bb_by_date = {}
            if body_battery_data and 'bodyBatteryValues' in body_battery_data:
                for entry in body_battery_data['bodyBatteryValues']:
                    if 'date' in entry:
                        date_key = entry['date'][:10] if len(entry['date']) >= 10 else entry['date']
                        bb_by_date[date_key] = entry
        except Exception as e:
            print(f"[garmin] Body battery not available: {e}")
            bb_by_date = {}

        count = 0
        for a in activities:
            garmin_id    = a.get("activityId")
            name         = a.get("activityName", "Activity")
            atype        = a.get("activityType", {}).get("typeKey", "unknown")
            distance_km  = round(a.get("distance", 0) / 1000, 2) if a.get("distance") else 0.0
            duration_min = round(a.get("duration", 0) / 60, 1) if a.get("duration") else 0.0
            avg_hr       = a.get("averageHR")
            calories     = a.get("calories")

            # Get start date from activity startTimeLocal
            start_time = a.get("startTimeLocal", "")
            start_date_str = start_time[:10] if start_time else datetime.now().strftime("%Y-%m-%d")

            # Try to get body battery for activity date
            bb_start = None
            bb_end = None
            if start_date_str in bb_by_date:
                bb_entry = bb_by_date[start_date_str]
                bb_start = bb_entry.get('bodyBatteryStartValue')
                bb_end = bb_entry.get('bodyBatteryEndValue')

            # Map activity type
            try:
                mapped_type = _map_activity_type(atype)
            except Exception as e:
                print(f"[garmin] Error mapping activity type '{atype}': {e}")
                import traceback
                traceback.print_exc()
                mapped_type = "other"  # Default fallback

            database.insert_activity(
                garmin_id, name, mapped_type, distance_km, duration_min,
                avg_hr, calories, bb_start, bb_end, start_date_str
            )
            count += 1

        print(f"[garmin] Pulled {count} activities.")
        return count

    except Exception as e:
        print(f"[garmin] Error pulling activities: {e}")
        print(f"[garmin] Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return 0
