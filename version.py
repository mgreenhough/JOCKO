"""Version information utility - provides actual running version."""

import subprocess
import os
import database

# Store version at module load time (when bot starts)
_version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".version")


def _get_git_version():
    """Get git commit hash - should only be called at startup."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def initialize_version():
    """Store version at bot startup. Call this once when main.py loads."""
    version = _get_git_version()
    try:
        with open(_version_file, "w") as f:
            f.write(version)
        # Also store in database for redundancy
        database.set_setting("running_version", version)
    except Exception:
        pass
    return version


def get_running_version():
    """
    Get the version that's actually running (not git).
    Returns the stored version from startup.
    """
    # First try the version file
    if os.path.exists(_version_file):
        try:
            with open(_version_file, "r") as f:
                version = f.read().strip()
                if version:
                    return version
        except Exception:
            pass
    
    # Fallback to database
    try:
        version = database.get_setting("running_version")
        if version:
            return version
    except Exception:
        pass
    
    # Last resort - get current git (may be wrong if code changed)
    return _get_git_version()


def get_version_string():
    """Get a formatted version string for display."""
    version = get_running_version()
    return f"v{version}"
