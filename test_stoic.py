"""Test the generated stoic file."""
from daily_stoic_ryan_holiday import get_daily_stoic_entry

# Test the 8 previously missing entries
test_dates = [
    (1, 8),   # January 8 - SEEING OUR ADDICTIONS
    (5, 5),   # May 5 - YOU ARE THE PROJECT
    (7, 29),  # July 29 - A CURE FOR THE SELF
    (9, 4),   # September 4
    (9, 23),  # September 23 - THE MOST SECURE FORTRESS
    (9, 28),  # September 28 - YOU HOLD THE TRUMP CARD
    (11, 14), # November 14 - YOU CHOOSE THE OUTCOME
    (12, 31), # December 31 - GET ACTIVE IN YOUR OWN RESCUE
]

print("Testing previously missing entries:")
print("=" * 60)

for month, day in test_dates:
    entry = get_daily_stoic_entry(month, day)
    print(f"\n{month}/{day}: {entry['title']}")
    print(f"  Author: {entry['author']}")
    print(f"  Quote: {entry['quote'][:80]}...")
    print(f"  Reflection: {entry['reflection'][:80]}...")

# Count total entries
from daily_stoic_ryan_holiday import DAILY_STOIC_ENTRIES
print(f"\n\nTotal entries: {len(DAILY_STOIC_ENTRIES)}")
