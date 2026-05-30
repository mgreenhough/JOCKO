"""Version information utility - provides git commit hash."""

import subprocess
import os


def get_git_version():
    """
    Get the short git commit hash for the current code version.
    Returns the 7-character short hash or 'unknown' if git is not available.
    """
    try:
        # Try to get the git commit hash from the current directory
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
    
    # Fallback: try to read from a version file (for deployment scenarios)
    version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".version")
    if os.path.exists(version_file):
        try:
            with open(version_file, "r") as f:
                return f.read().strip()
        except Exception:
            pass
    
    return "unknown"


def get_version_string():
    """Get a formatted version string for display."""
    version = get_git_version()
    return f"v{version}"