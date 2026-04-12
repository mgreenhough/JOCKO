import paypalrestsdk
import requests
from config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_RECIPIENT_EMAIL, PENALTY_AMOUNT
import database

# Configure PayPal SDK
PAYPAL_MODE = "live"  # Changed from "sandbox" to "live" for production
paypalrestsdk.configure({
    "mode": PAYPAL_MODE,
    "client_id": PAYPAL_CLIENT_ID,
    "client_secret": PAYPAL_CLIENT_SECRET
})


def _get_paypal_base_url():
    """Get the PayPal API base URL based on current mode."""
    return "https://api-m.paypal.com" if PAYPAL_MODE == "live" else "https://api-m.sandbox.paypal.com"


def _get_paypal_access_token():
    """Get OAuth access token for PayPal API calls."""
    base_url = _get_paypal_base_url()

    response = requests.post(
        f"{base_url}/v1/oauth2/token",
        headers={"Accept": "application/json", "Accept-Language": "en_US"},
        auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"}
    )

    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print(f"[payments] Failed to get access token: {response.text}")
        return None


def check_paypal_balance():
    """
    Check PayPal account balance.
    Returns dict with success status and balance info.
    """
    try:
        access_token = _get_paypal_access_token()
        if not access_token:
            return {"success": False, "error": "Could not authenticate with PayPal"}

        base_url = _get_paypal_base_url()

        response = requests.get(
            f"{base_url}/v1/reporting/balances",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )

        if response.status_code == 200:
            data = response.json()
            balances = data.get("balances", [])

            # Find AUD balance or return first available
            aud_balance = None
            for balance in balances:
                if balance.get("currency") == "AUD":
                    aud_balance = float(balance.get("available_balance", {}).get("value", 0))
                    break

            # If no AUD balance found, use first available
            if aud_balance is None and balances:
                aud_balance = float(balances[0].get("available_balance", {}).get("value", 0))

            return {
                "success": True,
                "balance": aud_balance or 0,
                "currency": "AUD",
                "raw_balances": balances
            }
        else:
            error_msg = response.json().get("message", response.text)
            print(f"[payments] Failed to get balance: {error_msg}")
            return {"success": False, "error": error_msg}

    except Exception as e:
        print(f"[payments] Exception checking balance: {e}")
        return {"success": False, "error": str(e)}


def verify_sufficient_funds(required_amount):
    """
    Verify PayPal account has sufficient funds for penalty.
    Returns dict with sufficient (bool) and balance info.
    """
    balance_check = check_paypal_balance()
    
    if not balance_check["success"]:
        return {
            "sufficient": False,
            "error": balance_check.get("error", "Unknown error"),
            "balance": None,
            "required": required_amount
        }
    
    available = balance_check["balance"]
    sufficient = available >= required_amount
    
    return {
        "sufficient": sufficient,
        "balance": available,
        "required": required_amount,
        "shortfall": max(0, required_amount - available) if not sufficient else 0
    }


def send_penalty(amount=None, recipient_email=None, week_start=None):
    """
    Send a penalty payout via PayPal Payouts API.
    Pre-checks balance before attempting payout.
    
    Args:
        amount: Amount to send (defaults to config.PENALTY_AMOUNT in live mode, $1 in sandbox)
        recipient_email: Email to send to (defaults to config)
        week_start: Week identifier for logging
    
    Returns:
        dict with success status and details
    """
    if recipient_email is None:
        recipient_email = PAYPAL_RECIPIENT_EMAIL
    
    # Determine amount based on mode
    if PAYPAL_MODE == "sandbox":
        # In sandbox mode, always use $1 for testing
        payout_amount = 1.00
    else:
        # In live mode, use provided amount or config amount
        if amount is None or amount <= 0:
            payout_amount = float(PENALTY_AMOUNT) if PENALTY_AMOUNT else 50.00
        else:
            payout_amount = float(amount)
    
    # Check balance before attempting payout
    print(f"[payments] Checking PayPal balance before ${payout_amount:.2f} AUD payout...")
    fund_check = verify_sufficient_funds(payout_amount)
    
    if not fund_check["sufficient"]:
        error_msg = fund_check.get("error", "Insufficient funds")
        balance = fund_check.get("balance")
        shortfall = fund_check.get("shortfall", payout_amount)
        
        print(f"[payments] INSUFFICIENT FUNDS: Balance=${balance}, Required=${payout_amount:.2f}, Shortfall=${shortfall:.2f}")
        
        return {
            "success": False,
            "error": f"Insufficient PayPal balance. Available: ${balance:.2f} AUD, Required: ${payout_amount:.2f} AUD, Shortfall: ${shortfall:.2f} AUD",
            "balance": balance,
            "required": payout_amount,
            "shortfall": shortfall,
            "insufficient_funds": True
        }
    
    print(f"[payments] Sufficient funds confirmed: ${fund_check['balance']:.2f} AUD available")
    
    payout = paypalrestsdk.Payout({
        "sender_batch_header": {
            "sender_batch_id": f"penalty_{week_start or 'test'}_{database.get_connection().execute('SELECT datetime(\"now\")').fetchone()[0]}",
            "email_subject": "Accountability Penalty - Goal Not Met",
            "email_message": "You missed your weekly fitness goal. This penalty has been sent as agreed."
        },
        "items": [{
            "recipient_type": "EMAIL",
            "amount": {
                "value": f"{payout_amount:.2f}",
                "currency": "AUD"
            },
            "receiver": recipient_email,
            "note": "Accountability penalty for missed fitness goal",
            "sender_item_id": f"penalty_item_{week_start or 'test'}"
        }]
    })
    
    try:
        if payout.create(sync_mode=False):
            result = {
                "success": True,
                "payout_batch_id": payout.batch_header.payout_batch_id,
                "amount": payout_amount,
                "recipient": recipient_email,
                "status": payout.batch_header.batch_status
            }
            print(f"[payments] Penalty payout created: {result}")
            return result
        else:
            error = {
                "success": False,
                "error": payout.error
            }
            print(f"[payments] Payout failed: {error}")
            return error
    except Exception as e:
        error = {
            "success": False,
            "error": str(e)
        }
        print(f"[payments] Exception during payout: {e}")
        return error


def get_payout_status(payout_batch_id):
    """Check the status of a payout."""
    try:
        payout = paypalrestsdk.Payout.find(payout_batch_id)
        return {
            "batch_status": payout.batch_header.batch_status,
            "time_created": payout.batch_header.time_created,
            "time_completed": getattr(payout.batch_header, 'time_completed', None)
        }
    except Exception as e:
        return {"error": str(e)}


def set_mode(mode):
    """Set PayPal mode (sandbox or live)."""
    global PAYPAL_MODE
    PAYPAL_MODE = mode
    paypalrestsdk.configure({
        "mode": PAYPAL_MODE,
        "client_id": PAYPAL_CLIENT_ID,
        "client_secret": PAYPAL_CLIENT_SECRET
    })
    print(f"[payments] PayPal mode set to: {mode}")


def check_and_clear_pause_if_sufficient_funds():
    """
    Check if PayPal now has sufficient funds and clear the pause if so.
    Used by /revive command to resume after adding funds.
    Returns dict with paused status and details.
    """
    # Check if paused
    is_paused = database.get_setting("jocko_paused") == "1"
    reason = database.get_setting("jocko_paused_reason") or ""

    # Only check/clear if paused for insufficient_funds
    if not is_paused or reason != "insufficient_funds":
        return {"paused": False, "reason": reason or None}

    penalty_amount = float(database.get_setting("penalty_amount") or 0)

    # If no penalty amount, just clear the pause
    if penalty_amount <= 0:
        database.set_setting("jocko_paused", "0")
        database.set_setting("jocko_paused_reason", "")
        return {"paused": False, "reason": None, "balance": None, "required": 0}

    # Verify funds
    fund_check = verify_sufficient_funds(penalty_amount)

    if fund_check["sufficient"]:
        # Sufficient funds - clear the pause
        database.set_setting("jocko_paused", "0")
        database.set_setting("jocko_paused_reason", "")
        print(f"[payments] BOT RESUMED: Sufficient funds available (${fund_check['balance']:.2f} AUD)")

        return {
            "paused": False,
            "reason": None,
            "balance": fund_check.get("balance"),
            "required": penalty_amount
        }
    else:
        # Still insufficient - keep paused
        return {
            "paused": True,
            "reason": "insufficient_funds",
            "balance": fund_check.get("balance"),
            "required": penalty_amount,
            "shortfall": fund_check.get("shortfall", penalty_amount)
        }


def get_pause_status():
    """
    Get current pause status of the bot.
    Returns dict with paused status and details.
    """
    is_paused = database.get_setting("jocko_paused") == "1"
    reason = database.get_setting("jocko_paused_reason") or ""
    paused_at = database.get_setting("jocko_paused_at") or ""

    if not is_paused:
        return {"paused": False}

    # Get current balance for display
    balance_check = check_paypal_balance()
    balance = balance_check.get("balance") if balance_check.get("success") else None
    penalty_amount = float(database.get_setting("penalty_amount") or 0)

    return {
        "paused": True,
        "reason": reason,
        "paused_at": paused_at,
        "balance": balance,
        "required": penalty_amount
    }