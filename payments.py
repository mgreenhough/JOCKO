import paypalrestsdk
from config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_RECIPIENT_EMAIL, PENALTY_AMOUNT
import database

# Configure PayPal SDK
PAYPAL_MODE = "sandbox"  # Change to "live" for production
paypalrestsdk.configure({
    "mode": PAYPAL_MODE,
    "client_id": PAYPAL_CLIENT_ID,
    "client_secret": PAYPAL_CLIENT_SECRET
})


def send_penalty(amount=None, recipient_email=None, week_start=None):
    """
    Send a penalty payout via PayPal Payouts API.
    
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
        "mode": mode,
        "client_id": PAYPAL_CLIENT_ID,
        "client_secret": PAYPAL_CLIENT_SECRET
    })
    print(f"[payments] PayPal mode set to: {mode}")
