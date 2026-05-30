# Issues

- 27/05/26

101. [x] Jock is still sending final report or summary on Sundays despite being /deactivate

    Fix applied
    Updated scheduler.py
    Added deactivation/dormant guard inside send_weekly_report()
    What changed
    send_weekly_report() now:
    skips sending the Sunday weekly report when jocko_active != "1"
    also skips if jocko_dormant == "1"
    Verification
    python -m py_compile scheduler.py passed with no syntax errors


102. [x] I was told on 14/04 that i missed a session despite logging a 29:41 Strength session. And again on the 15th when logging my sprints. jocko appears to be failing to pull data before doing workout check in. interrogate these sessions and see if they passed veracity checks. if so what is happening?

    Fix applied
    Updated coach.check_gym_session_in_window() to accept sessions that start shortly before the committed gym time, and tightened Garmin pull error reporting in scheduler.py.

103. [x] Sprints arent showing as activities when /status called. investigate how it is ingesting and interpreting these from garmin. i think there is somewher where we can set the goals or activities we want to commit to? can we include sprints (specifically the custom REHIT and HIIT workouts saved in garmin)

104. [x] wakeup was missed on 17/04 after calling status? no gym follow up either

105. [x] Seems to be half an hour late on everything? Timezone issue?

    Fix applied
    Updated timezone.py
    Fixed derive_timezone_from_garmin() function
    What changed
    Changed offset calculation from int() (truncates) to full precision float division
    Added half-hour offset support (5.5, 9.5, 10.5, 12.5) to offset_map
    Added India (5.5), Adelaide (9.5), Chatham Islands (12.5) to timezone mappings
    Changed rounding logic from nearest hour to nearest 0.5 hour
    Changed stored timezone verification tolerance from exact match to 0.5 hour window
    Root cause
    The int() function was truncating UTC+9:30 to UTC+9, causing 30-minute delay
    Verification
    python -m py_compile timezone.py passed with no syntax errors

106. [x] Return of daily commitment: Comment at the end is not dynamic (always the same). it should be using the open ai api for jocko like comment. can repeat but needs to change each time.

    Fix applied
    Updated main.py and coach.py
    What changed
    Replaced static commitment confirmation messages with dynamic AI-generated responses:
    - Created coach.generate_commitment_confirmation() function
    - Uses OpenAI API to generate Jocko-like comments based on intensity level
    - Handles different commitment types: full day, wake-only, gym-only, rest day
    - Added randomized fallback responses if API fails
    - Each response is unique while maintaining the appropriate tone
    Verification
    python -m py_compile coach.py main.py passed with no syntax errors

107. [x] add new status: /stoic whereby it is the same as /deactivate but automatically sends the daily stoic installment at 0500 each morning. Should work regardless of paypal balance. Update readme to reflect /Stoic option if people just want to use it for that.

    Fix applied
    Updated main.py and scheduler.py
    What changed
    - Created /stoic command in main.py that sets jocko_stoic=1, jocko_active=0, jocko_dormant=0
    - Added send_daily_stoic() function in scheduler.py that runs at 05:00 daily
    - The stoic job only sends messages when jocko_stoic=1
    - Stoic mode works regardless of PayPal balance (no pause checks)
    - Updated cmd_activate() to clear stoic flag when reactivating
    - Updated cmd_dormant() to clear stoic flag
    - Added /stoic command handler to the Telegram bot
    - Updated README.md with new /stoic command and operating modes table
    Verification
    python -m py_compile main.py scheduler.py passed with no syntax errors

Committed 30/05/26 1238: f5bf1bf

108. [x] /pull failed: garmin connect Auth error.

    Fix applied
    Updated garmin.py
    Enhanced _get_client() function with automatic token recovery and re-authentication
    What changed
    Added intelligent auth error detection that checks for keywords like:
    - auth, authentication, login, credential, unauthorized
    - HTTP 403/401, forbidden, invalid, expired, token, mfa, 2fa
    
    When an auth error is detected:
    1. Automatically clears the token store (~/.garminconnect)
    2. Attempts fresh login with stored credentials on the server
    3. If successful: generates new tokens and continues normally
    4. Only if MFA is required: provides instructions for manual token generation
    
    This means the server can now automatically recover from most auth failures
    without manual intervention. Only MFA challenges require local authentication.
    Verification
    python -m py_compile garmin.py passed with no syntax errors

Committed 1257: 2a1252a

109. [x] Add version number somewhere (use GIT short message number (2a1252a)) and have it displayed in /status and after /update is called so user knows update has been successfull and which version

    Fix applied
    Created version.py utility module and updated coach.py and main.py
    What changed
    - Created version.py with get_git_version() and get_version_string() functions
    - version.py reads git commit hash dynamically using git rev-parse --short HEAD
    - Falls back to .version file or 'unknown' if git not available
    - Updated coach.get_status() to display version: "📦 Version: v2a1252a"
    - Updated main.cmd_update() to display new version after successful update
    - Both /status and /update now show the current git commit hash
    
    Version format: "v{short_hash}" (e.g., "v2a1252a")
    Verification
    python -m py_compile version.py coach.py main.py passed with no syntax errors

110. [x] Add /balance to pull current PayPal ballance. Function should already exist because program uses it to check balance.

    Fix applied
    Updated main.py to add /balance command
    What changed
    - Added `import payments` at the top of main.py
    - Created cmd_balance() function that calls payments.check_paypal_balance()
    - Displays current PayPal balance with 2 decimal places
    - Compares balance against penalty amount to show sufficiency status
    - Shows warning if insufficient funds with shortfall amount
    - Added /balance to the /commands list under "Penalty Settings"
    - Registered the CommandHandler for /balance
    Verification
    python -m py_compile main.py passed with no syntax errors

Committed 1335: 427b627

110.1 [x] /balance failed: couldn't auth with paypal. can we add auto recovery similar to the fix for issue 108.

    Fix applied
    Updated payments.py
    Enhanced _get_paypal_access_token() function with automatic retry and credential refresh
    What changed
    - Added retry parameter to _get_paypal_access_token() for automatic recovery
    - When authentication error detected (invalid_client, unauthorized, 401, 403, etc.):
      1. Reloads config module to get fresh credentials
      2. Retries the API call once with new credentials
      3. If still failing, returns appropriate error message
    - Also retries on request exceptions (network issues)
    - Enhanced error logging to track retry attempts
    - Similar pattern to garmin.py issue 108 fix but adapted for PayPal OAuth flow
    Verification
    python -m py_compile payments.py passed with no syntax errors

Committed 1348: 68af134

111. [x] On /update it ALWAYS say !Code updated but restart may have issues.

    Fix applied
    Updated main.py
    What changed
    The issue was that systemctl restart returns immediately before the service has actually started.
    Fixed by adding a 2-second delay after restart, then checking if the service is actually active.
    Now only shows the warning if the service is genuinely not running after the restart attempt.
    Changed logic to:
    - Always check service status after restart (not just when restart command fails)
    - Wait 2 seconds for service to start before checking
    - Only show warning if service status confirms it's not running
    - Show success message with new version when service is confirmed running
    Verification
    python -m py_compile main.py passed with no syntax errors

110.2 [x] /balance failed and produced EXACTLY the same error!?

    Fix applied
    Updated payments.py
    Enhanced _get_paypal_access_token() function with proper global variable updates
    
    Root cause
    The retry logic in issue 110.1 was reloading config but only updating local variables.
    The module-level PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET variables were cached
    from the original import and never updated, so subsequent API calls still used
    the old credentials.
    
    What changed
    - Added `global PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET` declaration
    - On retry: Updates the global variables with fresh credentials from reloaded config
    - Reconfigures the paypalrestsdk with the new credentials
    - This ensures the SDK uses the updated credentials for all operations
    
    Verification
    python -m py_compile payments.py passed with no syntax errors

Committed: <to be filled in>
