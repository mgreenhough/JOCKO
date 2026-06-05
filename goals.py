import database

# --- Default values ---
# Edit these when you want to change your goals.
# These are only used if no goals have been saved to the database yet.

DEFAULTS = {
    "activities_per_week": 6,    # active — total training sessions
    "workouts_per_week":   4,    # active — strength/resistance sessions
    "cardio_per_week":     4,    # active — cardiovascular sessions
    "sprints_per_week":    2,    # active — high-intensity sprint sessions
    "steps_per_day":       None, # placeholder — enabled when Garmin steps become a goal
    "calories_per_week":   None, # placeholder — enabled when calories become a goal
    "distance_per_week":   None, # placeholder — enabled when distance becomes a goal
}

ACTIVE_GOALS = ["activities_per_week", "workouts_per_week", "cardio_per_week", "sprints_per_week"]
PLACEHOLDER_GOALS = ["steps_per_day", "calories_per_week", "distance_per_week"]
ALL_GOALS = ACTIVE_GOALS + PLACEHOLDER_GOALS


def get():
    saved = database.get_goals()
    if saved:
        return saved
    return DEFAULTS.copy()


def _normalize_goal_key(key):
    """
    Normalize goal key input to handle various formats:
    - activities_per_week, activitiesperweek, activities, act, a
    - workouts_per_week, workoutsperweek, workouts, workout, wo, w
    - cardio_per_week, cardioperweek, cardio, card, c
    - sprints_per_week, sprintsperweek, sprints, sprint, sp, s
    - steps_per_day, stepsperday, steps, step
    - calories_per_week, caloriesperweek, calories, cal, cals
    - distance_per_week, distanceperweek, distance, dist, d
    """
    if not key:
        return None
    
    # Convert to lowercase and remove all non-alphanumeric characters
    normalized = ''.join(c for c in key.lower() if c.isalnum())
    
    # Map normalized forms to canonical keys
    mappings = {
        # activities_per_week
        'activities_per_week': 'activities_per_week',
        'activitiesperweek': 'activities_per_week',
        'activityperweek': 'activities_per_week',
        'activities': 'activities_per_week',
        'activity': 'activities_per_week',
        'act': 'activities_per_week',
        'a': 'activities_per_week',
        
        # workouts_per_week
        'workouts_per_week': 'workouts_per_week',
        'workoutsperweek': 'workouts_per_week',
        'workoutperweek': 'workouts_per_week',
        'workouts': 'workouts_per_week',
        'workout': 'workouts_per_week',
        'wo': 'workouts_per_week',
        'w': 'workouts_per_week',
        
        # cardio_per_week
        'cardio_per_week': 'cardio_per_week',
        'cardioperweek': 'cardio_per_week',
        'cardio': 'cardio_per_week',
        'card': 'cardio_per_week',
        
        # sprints_per_week
        'sprints_per_week': 'sprints_per_week',
        'sprintsperweek': 'sprints_per_week',
        'sprintperweek': 'sprints_per_week',
        'sprints': 'sprints_per_week',
        'sprint': 'sprints_per_week',
        'sp': 'sprints_per_week',
        's': 'sprints_per_week',
        
        # steps_per_day
        'steps_per_day': 'steps_per_day',
        'stepsperday': 'steps_per_day',
        'stepperday': 'steps_per_day',
        'steps': 'steps_per_day',
        'step': 'steps_per_day',
        
        # calories_per_week
        'calories_per_week': 'calories_per_week',
        'caloriesperweek': 'calories_per_week',
        'calorieperweek': 'calories_per_week',
        'calories': 'calories_per_week',
        'calorie': 'calories_per_week',
        'cals': 'calories_per_week',
        'cal': 'calories_per_week',
        'c': 'calories_per_week',
        
        # distance_per_week
        'distance_per_week': 'distance_per_week',
        'distanceperweek': 'distance_per_week',
        'distances': 'distance_per_week',
        'distance': 'distance_per_week',
        'dist': 'distance_per_week',
        'd': 'distance_per_week',
    }
    
    return mappings.get(normalized)


def set(key, value):
    normalized_key = _normalize_goal_key(key)
    if normalized_key is None or normalized_key not in ALL_GOALS:
        raise ValueError(f"Unknown goal '{key}'. Valid: {', '.join(ALL_GOALS)}")
    database.set_goal(normalized_key, value)


def is_active(key):
    goals = get()
    return goals.get(key) is not None


def compliance(current):
    goals = get()
    lines = []

    # Activities (total)
    if goals.get("activities_per_week"):
        act_pct = round((current["activity_count"] / goals["activities_per_week"]) * 100)
        lines.append(f"Activities: {current['activity_count']} / {goals['activities_per_week']} ({act_pct}%)")
    
    # Workouts (strength/resistance)
    if goals.get("workouts_per_week"):
        workout_pct = round((current["workout_count"] / goals["workouts_per_week"]) * 100)
        lines.append(f"Workouts: {current['workout_count']} / {goals['workouts_per_week']} ({workout_pct}%)")
    
    # Cardio
    if goals.get("cardio_per_week"):
        cardio_pct = round((current["cardio_count"] / goals["cardio_per_week"]) * 100)
        lines.append(f"Cardio: {current['cardio_count']} / {goals['cardio_per_week']} ({cardio_pct}%)")
    
    # Sprints
    if goals.get("sprints_per_week"):
        sprint_pct = round((current["sprint_count"] / goals["sprints_per_week"]) * 100)
        lines.append(f"Sprints: {current['sprint_count']} / {goals['sprints_per_week']} ({sprint_pct}%)")

    if goals.get("calories_per_week"):
        cal_pct = round((current["total_calories"] / goals["calories_per_week"]) * 100)
        lines.append(f"Calories: {current['total_calories']} / {goals['calories_per_week']} kcal ({cal_pct}%)")

    if goals.get("distance_per_week"):
        dist_pct = round((current["total_distance"] / goals["distance_per_week"]) * 100)
        lines.append(f"Distance: {current['total_distance']} / {goals['distance_per_week']} km ({dist_pct}%)")

    return "\n".join(lines)


def check_compliance(current):
    goals = get()
    
    # Check all active goals
    activities_met = current.get("activity_count", 0) >= goals.get("activities_per_week", 0) if goals.get("activities_per_week") else True
    workouts_met = current.get("workout_count", 0) >= goals.get("workouts_per_week", 0) if goals.get("workouts_per_week") else True
    cardio_met = current.get("cardio_count", 0) >= goals.get("cardio_per_week", 0) if goals.get("cardio_per_week") else True
    sprints_met = current.get("sprint_count", 0) >= goals.get("sprints_per_week", 0) if goals.get("sprints_per_week") else True
    
    # All active goals must be met
    all_active_met = activities_met and workouts_met and cardio_met and sprints_met
    
    return {
        "activities_met": activities_met,
        "workouts_met":   workouts_met,
        "cardio_met":     cardio_met,
        "sprints_met":    sprints_met,
        "all_met":        all_active_met,
        "current":        current,
        "goals":          goals,
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
