from datetime import datetime, timedelta
from garminconnect import Garmin
from config import GARMIN_EMAIL, GARMIN_PASSWORD
import database

_client = None

def _get_client():
    global _client
    if _client is None:
        if not GARMIN_EMAIL or not GARMIN_PASSWORD:
            print("[garmin] No credentials provided — using dummy data.")
            return None
        try:
            _client = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
            _client.login()
            print("[garmin] Logged in successfully.")
        except Exception as e:
            print(f"[garmin] Login failed: {e}")
            return None
    return _client

def _seed_dummy_data():
    today = datetime.now()
    dummy = [
        (1001, "Sprint Session", "sprint",   0.0,  45.0, 168, 520, 72, 48, (today - timedelta(days=1)).strftime("%Y-%m-%d")),
        (1002, "Strength",       "strength", 0.0,  60.0, 135, 410, 80, 58, (today - timedelta(days=2)).strftime("%Y-%m-%d")),
        (1003, "Sprint Session", "sprint",   0.0,  40.0, 172, 480, 65, 40, (today - timedelta(days=3)).strftime("%Y-%m-%d")),
        (1004, "Strength",       "strength", 0.0,  60.0, 140, 430, 85, 62, (today - timedelta(days=5)).strftime("%Y-%m-%d")),
        (1005, "Strength",       "strength", 0.0,  55.0, 130, 380, 78, 55, (today - timedelta(days=6)).strftime("%Y-%m-%d")),
        (1006, "Sprint Session", "sprint",   0.0,  42.0, 165, 490, 70, 44, (today - timedelta(days=8)).strftime("%Y-%m-%d")),
        (1007, "Strength",       "strength", 0.0,  60.0, 138, 400, 82, 60, (today - timedelta(days=9)).strftime("%Y-%m-%d")),
        (1008, "Strength",       "strength", 0.0,  65.0, 142, 450, 88, 65, (today - timedelta(days=10)).strftime("%Y-%m-%d")),
    ]
    for row in dummy:
        database.insert_activity(*row)
    print("[garmin] Dummy data seeded.")

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
        _seed_dummy_data()
        return

    try:
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()

        # Get activities in date range
        activities = client.get_activities_by_date(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )

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
            mapped_type = _map_activity_type(atype)

            database.insert_activity(
                garmin_id, name, mapped_type, distance_km, duration_min,
                avg_hr, calories, bb_start, bb_end, start_date_str
            )
            count += 1

        print(f"[garmin] Pulled {count} activities.")

    except Exception as e:
        print(f"[garmin] Error pulling activities: {e}")
        print("[garmin] Falling back to dummy data.")
        _seed_dummy_data()
