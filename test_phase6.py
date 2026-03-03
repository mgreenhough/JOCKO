"""
Phase 6 End-to-End Test
Tests proactive prompting with intensity and frequency settings.
"""
import asyncio
import sys
sys.path.insert(0, '.')

import database
database.init_db()

from scheduler import (
    morning_check_in,
    midday_nudge,
    evening_warning,
    breach_alert,
    sunday_preweek_planning
)

async def test_phase6():
    print("=" * 60)
    print("PHASE 6 END-TO-END TEST: Proactive Prompting + Intensity/Frequency")
    print("=" * 60)
    print()
    
    # Get current settings
    intensity = int(database.get_setting("intensity") or 5)
    frequency = int(database.get_setting("frequency") or 5)
    
    print(f"Current Settings:")
    print(f"  - Intensity: {intensity}")
    print(f"  - Frequency: {frequency}")
    print()
    
    # Test 1: Set intensity to 9, frequency to 9
    print("TEST 1: Setting intensity=9, frequency=9 (high tone, high contact)")
    print("-" * 60)
    database.set_setting("intensity", "9")
    database.set_setting("frequency", "9")
    
    print("Running morning_check_in()...")
    await morning_check_in()
    print()
    
    print("Running midday_nudge()...")
    await midday_nudge()
    print()
    
    print("Running evening_warning()...")
    await evening_warning()
    print()
    
    print("Running breach_alert()...")
    await breach_alert()
    print()
    
    print("Running sunday_preweek_planning()...")
    await sunday_preweek_planning()
    print()
    
    # Test 2: Set intensity to 2, frequency to 2
    print("TEST 2: Setting intensity=2, frequency=2 (soft tone, low contact)")
    print("-" * 60)
    database.set_setting("intensity", "2")
    database.set_setting("frequency", "2")
    
    print("Running morning_check_in()...")
    await morning_check_in()
    print()
    
    print("Running midday_nudge()... (should NOT send - frequency < 7)")
    await midday_nudge()
    print()
    
    print("Running evening_warning()... (should NOT send - frequency < 4)")
    await evening_warning()
    print()
    
    print("Running breach_alert()... (should NOT send - frequency < 4)")
    await breach_alert()
    print()
    
    print("Running sunday_preweek_planning()...")
    await sunday_preweek_planning()
    print()
    
    # Test 3: Set intensity to 5, frequency to 5 (default)
    print("TEST 3: Setting intensity=5, frequency=5 (default)")
    print("-" * 60)
    database.set_setting("intensity", "5")
    database.set_setting("frequency", "5")
    
    print("Running morning_check_in()...")
    await morning_check_in()
    print()
    
    print("Running midday_nudge()... (should NOT send - frequency < 7)")
    await midday_nudge()
    print()
    
    print("Running evening_warning()...")
    await evening_warning()
    print()
    
    print("Running breach_alert()...")
    await breach_alert()
    print()
    
    print("Running sunday_preweek_planning()...")
    await sunday_preweek_planning()
    print()
    
    # Restore original settings
    print("Restoring original settings...")
    database.set_setting("intensity", str(intensity))
    database.set_setting("frequency", str(frequency))
    
    print()
    print("=" * 60)
    print("PHASE 6 END-TO-END TEST COMPLETE")
    print("=" * 60)
    print()
    print("Check your Telegram for messages with different tones.")
    print("High intensity (9) should be aggressive/direct.")
    print("Low intensity (2) should be supportive/friendly.")

if __name__ == "__main__":
    asyncio.run(test_phase6())
