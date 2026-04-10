#!/usr/bin/env python3
"""Test Garmin login to diagnose rate limiting issue."""

from garminconnect import Garmin
import os

email = 'mattgreenhough@hotmail.com'
password = 'XMeu5XC-VqKz.a('
tokenstore = os.path.expanduser('~/.garminconnect')

print('Testing Garmin login...')
print(f'Token store: {tokenstore}')

try:
    client = Garmin(email, password)
    client.login(tokenstore)
    print('Login successful!')
    
    # Test fetching activities
    activities = client.get_activities(0, 5)
    print(f'Found {len(activities)} activities')
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
