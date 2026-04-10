import sqlite3
from datetime import datetime
from config import DB_PATH
import timezone

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            start_time TEXT,
            duration INTEGER,
            distance REAL,
            calories REAL,
            avg_hr INTEGER,
            max_hr INTEGER,
            body_battery_start INTEGER,
            body_battery_end INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workouts_per_week INTEGER DEFAULT 4,
            sprints_per_week INTEGER DEFAULT 2,
            steps_per_day INTEGER,
            calories_per_week INTEGER,
            distance_per_week REAL,
            updated_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS penalty_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT,
            goal_workouts REAL,
            actual_workouts REAL,
            goal_sprints REAL,
            actual_sprints REAL,
            penalty_amount REAL,
            paid INTEGER DEFAULT 0,
            recipient_email TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT,
            timestamp TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id TEXT,
            flag_type TEXT,
            reason TEXT,
            timestamp TEXT,
            FOREIGN KEY(activity_id) REFERENCES activities(id)
        )
    """)

    conn.commit()

    c.execute("""
        CREATE TABLE IF NOT EXISTS weekly_summary (
            id INTEGER PRIMARY KEY,
            week_start TEXT UNIQUE,
            total_distance REAL,
            total_time REAL,
            avg_hr REAL,
            total_calories REAL,
            compliance_pct REAL,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_commitments (
            id INTEGER PRIMARY KEY,
            date TEXT UNIQUE,
            wakeup_time TEXT,
            gym_time TEXT,
            created_at TEXT
        )
    """)

    defaults = [
        ("intensity", "5"),
        ("frequency", "5"),
        ("penalty_amount", "50"),
        ("recipient_email", ""),
        ("jocko_active", "1"),  # Default to active
        ("penalty_start_date", ""),  # Empty means no delay
        ("timezone", ""),  # IANA timezone name, empty until detected
    ]
    for key, value in defaults:
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

    conn.commit()
    conn.close()

def get_setting(key):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_setting(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_goals():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT workouts_per_week, sprints_per_week, steps_per_day, calories_per_week, distance_per_week FROM goals ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "workouts_per_week": row[0],
            "sprints_per_week": row[1],
            "steps_per_day": row[2],
            "calories_per_week": row[3],
            "distance_per_week": row[4],
        }
    return {
        "workouts_per_week": 4,
        "sprints_per_week": 2,
        "steps_per_day": None,
        "calories_per_week": None,
        "distance_per_week": None,
    }

def set_goal(key, value):
    from datetime import datetime
    conn = get_connection()
    c = conn.cursor()
    current = get_goals()
    current[key] = value
    c.execute("""
        INSERT INTO goals
        (workouts_per_week, sprints_per_week, steps_per_day, calories_per_week, distance_per_week, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        current["workouts_per_week"],
        current["sprints_per_week"],
        current["steps_per_day"],
        current["calories_per_week"],
        current["distance_per_week"],
        timezone.now_utc().isoformat()
    ))
    conn.commit()
    conn.close()

def insert_activity(garmin_id, name, activity_type, distance_km, duration_min, avg_hr, calories, body_battery_start, body_battery_end, start_time_utc):
    """Insert activity with start_time in UTC ISO format."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO activities
        (id, name, type, distance, duration, avg_hr, calories, body_battery_start, body_battery_end, start_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(garmin_id), name, activity_type, distance_km, duration_min, avg_hr, calories, body_battery_start, body_battery_end, start_time_utc))
    conn.commit()
    conn.close()

def get_activities_since(date_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM activities WHERE start_time >= ? ORDER BY start_time DESC", (date_str,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_activities_between(start_date_str, end_date_str):
    """Get activities within a date range (inclusive start, exclusive end)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM activities WHERE start_time >= ? AND start_time < ? ORDER BY start_time DESC", (start_date_str, end_date_str))
    rows = c.fetchall()
    conn.close()
    return rows

def get_latest_body_battery():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT body_battery_end FROM activities WHERE body_battery_end IS NOT NULL ORDER BY start_time DESC, id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def save_conversation(role, content):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO conversations (role, content, created_at) VALUES (?, ?, ?)",
              (role, content, timezone.now_utc().isoformat()))
    conn.commit()
    conn.close()

def get_recent_conversations(limit):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return list(reversed(rows))

def save_daily_commitment(date_str, wakeup_time, gym_time):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO daily_commitments (date, wakeup_time, gym_time, created_at)
        VALUES (?, ?, ?, ?)
    """, (date_str, wakeup_time, gym_time, timezone.now_utc().isoformat()))
    conn.commit()
    conn.close()

def get_daily_commitment(date_str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT wakeup_time, gym_time FROM daily_commitments WHERE date = ?", (date_str,))
    row = c.fetchone()
    conn.close()
    return row

def log_penalty(week_start, goal_workouts, actual_workouts, goal_sprints, actual_sprints, penalty_amount, paid, recipient_email):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO penalty_log
        (week_start, goal_workouts, actual_workouts, goal_sprints, actual_sprints, penalty_amount, paid, recipient_email, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (week_start, goal_workouts, actual_workouts, goal_sprints, actual_sprints, penalty_amount, paid, recipient_email, timezone.now_utc().isoformat()))
    conn.commit()
    conn.close()