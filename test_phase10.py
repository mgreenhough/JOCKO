#!/usr/bin/env python3
"""Test Phase 10 activity classification."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coach import classify_activity

# Test classification
test_cases = [
    ('Running', {'is_cardio': True, 'is_workout': False, 'is_sprint': False}),
    ('Sprint Running', {'is_cardio': True, 'is_workout': False, 'is_sprint': True}),
    ('Strength Training', {'is_cardio': False, 'is_workout': True, 'is_sprint': False}),
    ('CrossFit', {'is_cardio': False, 'is_workout': True, 'is_sprint': False}),
    ('HIIT', {'is_cardio': True, 'is_workout': False, 'is_sprint': True}),
    ('Yoga', {'is_cardio': False, 'is_workout': False, 'is_sprint': False}),
    ('Cycling', {'is_cardio': True, 'is_workout': False, 'is_sprint': False}),
    ('REHIT', {'is_cardio': False, 'is_workout': False, 'is_sprint': True}),
]

print('Testing activity classification:')
print('=' * 50)

all_passed = True
for activity_type, expected in test_cases:
    result = classify_activity(activity_type)
    passed = all(result[k] == expected[k] for k in expected)
    status = '✅' if passed else '❌'
    if not passed:
        all_passed = False
        print(f'{status} "{activity_type}"')
        print(f'   Expected: {expected}')
        print(f'   Got:      {result}')
    else:
        print(f'{status} "{activity_type}" → {result}')

print('=' * 50)
if all_passed:
    print('All tests passed!')
    sys.exit(0)
else:
    print('Some tests failed!')
    sys.exit(1)