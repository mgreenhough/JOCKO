import database

# --- Default values ---
# Edit these when you want to change your goals.
# These are only used if no goals have been saved to the database yet.

DEFAULTS = {
    "workouts_per_week": 4,      # active
    "sprints_per_week":  2,      # active
    "steps_per_day":     None,   # placeholder — enable when Garmin steps available
    "calories_per_week": None,   # placeholder — enable when calorie tracking added
    "distance_per_week": None,   # placeholder — enable when distance becomes a goal
}

ACTIVE_GOALS = ["workouts_per_week", "sprints_per_week"]
PLACEHOLDER_GOALS = ["steps_per_day", "calories_per_week", "distance_per_week"]
ALL_GOALS = ACTIVE_GOALS + PLACEHOLDER_GOALS


def get():
    saved = database.get_goals()
    if saved:
        return saved
    return DEFAULTS.copy()


def set(key, value):
    if key not in ALL_GOALS:
        raise ValueError(f"Unknown goal '{key}'. Valid: {', '.join(ALL_GOALS)}")
    database.set_goal(key, value)


def is_active(key):
    goals = get()
    return goals.get(key) is not None


def compliance(current):
    goals = get()
    lines = []

    workout_pct = round((current["session_count"] / goals["workouts_per_week"]) * 100) if goals["workouts_per_week"] else 0
    sprint_pct  = round((current["sprint_count"]  / goals["sprints_per_week"])  * 100) if goals["sprints_per_week"]  else 0
    lines.append(f"Workouts: {current['session_count']} / {goals['workouts_per_week']} ({workout_pct}%)")
    lines.append(f"Sprints:  {current['sprint_count']}  / {goals['sprints_per_week']}  ({sprint_pct}%)")

    if goals.get("calories_per_week"):
        cal_pct = round((current["total_calories"] / goals["calories_per_week"]) * 100)
        lines.append(f"Calories: {current['total_calories']} / {goals['calories_per_week']} kcal ({cal_pct}%)")

    if goals.get("distance_per_week"):
        dist_pct = round((current["total_distance"] / goals["distance_per_week"]) * 100)
        lines.append(f"Distance: {current['total_distance']} / {goals['distance_per_week']} km ({dist_pct}%)")

    return "\n".join(lines)


def check_compliance(current):
    goals = get()
    workouts_met = current["session_count"] >= goals["workouts_per_week"]
    sprints_met  = current["sprint_count"]  >= goals["sprints_per_week"]
    return {
        "workouts_met": workouts_met,
        "sprints_met":  sprints_met,
        "all_met":      workouts_met and sprints_met,
        "current":      current,
        "goals":        goals,
    }


def summary_text():
    goals = get()
    lines = []
    for key in ACTIVE_GOALS:
        lines.append(f"{key}: {goals[key]}  (active)")
    for key in PLACEHOLDER_GOALS:
        val = goals.get(key)
        lines.append(f"{key}: {val if val is not None else 'not set'}")
    return "\n".join(lines)
