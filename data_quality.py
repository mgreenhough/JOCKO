import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple
from config import DB_PATH

# Flag types
FLAG_LOW_HEART_RATE = "low_avg_hr"
FLAG_HIGH_HEART_RATE = "high_avg_hr"
FLAG_FLATLINE_HEART_RATE = "flatline_hr"
FLAG_SHORT_DURATION = "short_duration"
FLAG_LONG_DURATION = "long_duration"

# Thresholds (customizable per activity type)
THRESHOLDS = {
    "running": {
        "min_avg_hr": 100,
        "max_avg_hr": 190,
        "min_duration": 600,  # 10 minutes
        "max_duration": 14400  # 4 hours
    },
    "cycling": {
        "min_avg_hr": 80,
        "max_avg_hr": 180,
        "min_duration": 600,
        "max_duration": 18000
    },
    "strength_training": {
        "min_avg_hr": 85,
        "max_avg_hr": 170,
        "min_duration": 1500,
        "max_duration": 7200
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
    activity_type = activity.get("activityType", {}).get("typeKey", "unknown")
    thresholds = THRESHOLDS.get(activity_type, {})
    
    # Skip analysis if no thresholds defined for activity type
    if not thresholds:
        return flags
    
    # Heart rate analysis
    avg_hr = activity.get("averageHeartRate", 0)
    max_hr = activity.get("maxHeartRate", 0)
    
    if avg_hr > 0:
        if avg_hr < thresholds.get("min_avg_hr", 0):
            flags.append((FLAG_LOW_HEART_RATE, f"Average heart rate ({avg_hr} bpm) unusually low for {activity_type}"))
        elif avg_hr > thresholds.get("max_avg_hr", 999):
            flags.append((FLAG_HIGH_HEART_RATE, f"Average heart rate ({avg_hr} bpm) unusually high for {activity_type}"))
            
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
            flags.append((FLAG_FLATLINE_HEART_RATE, f"Heart rate appears flatlined during {activity_type}"))
    
    # Duration analysis
    duration = activity.get("duration", 0)
    if duration > 0:
        if duration < thresholds.get("min_duration", 0):
            flags.append((FLAG_SHORT_DURATION, f"Duration ({duration}s) unusually short for {activity_type}"))
        elif duration > thresholds.get("max_duration", 999999):
            flags.append((FLAG_LONG_DURATION, f"Duration ({duration}s) unusually long for {activity_type}"))
    
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
        """, (activity_id, flag_type, description, datetime.now().isoformat()))
    
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