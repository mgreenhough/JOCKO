#!/usr/bin/env python3
"""Login to Garmin locally and generate tokens after rate limiting issue."""

from garminconnect import Garmin
import os

email = 'mattgreenhough@hotmail.com'
password = 'XMeu5XC-VqKz.a('
tokenstore = os.path.expanduser('~/.garminconnect')

print('Logging into Garmin to generate tokens...')
print(f'Tokens will be saved to: {tokenstore}')
print()

try:
    client = Garmin(email, password)
    client.login(tokenstore)
    print('Login successful!')
    print()
    print('Token files created:')
    for f in os.listdir(tokenstore):
        print(f'  - {f}')
    print()
    print('Now copy these files to the server:')
    print('  scp ~/.garminconnect/* root@203.57.51.49:~/.garminconnect/')
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
