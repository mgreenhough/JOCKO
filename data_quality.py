import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple
from config import DB_PATH
import timezone
from coach import classify_activity

# Flag types
FLAG_LOW_HEART_RATE = "low_avg_hr"
FLAG_FLATLINE_HEART_RATE = "flatline_hr"
FLAG_SHORT_DURATION = "short_duration"

# Thresholds (based on classified activity types: cardio, workout, sprint)
# Only minimum thresholds - no max HR or max duration
THRESHOLDS = {
    "cardio": {
        "min_avg_hr": 100,
        "min_duration": 900  # 15 minutes
    },
    "workout": {
        "min_avg_hr": 85,
        "min_duration": 1500  # 25 minutes
    },
    "sprint": {
        "min_avg_hr": 120,
        "min_duration": 600   # 10 minutes
    }
}

def analyze_activity(activity: Dict) -> List[Tuple[str, str]]:
    """
    Analyze an activity for potential data quality issues.
    
    Args:
        activity: Dictionary containing activity data
        
    Returns:
        List of (flag_type, description) tuples
    """
    flags = []
    
    # Get raw activity type and classify it
    raw_activity_type = activity.get("activityType", {}).get("typeKey", "unknown")
    classification = classify_activity(raw_activity_type)
    
    # Determine which category this activity falls into for threshold lookup
    # Priority: sprint > workout > cardio (sprint is most specific)
    if classification["is_sprint"]:
        activity_category = "sprint"
    elif classification["is_workout"]:
        activity_category = "workout"
    elif classification["is_cardio"]:
        activity_category = "cardio"
    else:
        # Activity doesn't match any category we have thresholds for
        return flags
    
    thresholds = THRESHOLDS.get(activity_category, {})
    
    # Skip analysis if no thresholds defined for activity type
    if not thresholds:
        return flags
    
    # Heart rate analysis - only check for LOW heart rate (no max)
    avg_hr = activity.get("averageHeartRate", 0)
    
    if avg_hr > 0:
        if avg_hr < thresholds.get("min_avg_hr", 0):
            flags.append((FLAG_LOW_HEART_RATE, f"Average heart rate ({avg_hr} bpm) unusually low for {activity_category}"))
            
    # Check for flatline heart rate (same value for 3+ consecutive minutes)
    heart_rate_samples = activity.get("heartRateSamples", [])
    if len(heart_rate_samples) > 3:
        flatline_detected = False
        for i in range(len(heart_rate_samples) - 3):
            if (heart_rate_samples[i][1] == heart_rate_samples[i+1][1] == 
                heart_rate_samples[i+2][1] == heart_rate_samples[i+3][1]):
                flatline_detected = True
                break
        if flatline_detected:
            flags.append((FLAG_FLATLINE_HEART_RATE, f"Heart rate appears flatlined during {activity_category}"))
    
    # Duration analysis - only check for SHORT duration (no max)
    duration = activity.get("duration", 0)
    if duration > 0:
        if duration < thresholds.get("min_duration", 0):
            flags.append((FLAG_SHORT_DURATION, f"Duration ({duration}s) unusually short for {activity_category}"))
    
    return flags

def save_flags(activity_id: int, flags: List[Tuple[str, str]]):
    """Save data quality flags to database."""
    if not flags:
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for flag_type, description in flags:
        cursor.execute("""
            INSERT INTO data_quality_flags (activity_id, flag_type, description, timestamp)
            VALUES (?, ?, ?, ?)
        """, (activity_id, flag_type, description, timezone.now_utc().isoformat()))
    
    conn.commit()
    conn.close()

def get_recent_flags(limit: int = 10) -> List[Dict]:
    """Retrieve recent data quality flags for reporting."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT df.activity_id, df.flag_type, df.description, df.timestamp, a.name
        FROM data_quality_flags df
        JOIN activities a ON df.activity_id = a.id
        ORDER BY df.timestamp DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "activity_id": row[0],
            "flag_type": row[1],
            "description": row[2],
            "timestamp": row[3],
            "activity_name": row[4]
        }
        for row in rows
    ]

def create_flags_table():
    """Create the data quality flags table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_quality_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER,
            flag_type TEXT,
            description TEXT,
            timestamp TEXT,
            FOREIGN KEY (activity_id) REFERENCES activities (id)
        )
    """)
    
    conn.commit()
    conn.close()