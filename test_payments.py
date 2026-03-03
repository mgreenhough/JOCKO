"""Test script for PayPal payments - uses $1 test amount."""
import os
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database
import payments
from config import PAYPAL_RECIPIENT_EMAIL

def test_payout():
    """Test PayPal payout with $1."""
    print("=" * 50)
    print("Testing PayPal Payout - $1 AUD")
    print("=" * 50)
    
    # Initialize database
    database.init_db()
    print("[test] Database initialized")
    
    # Test payout with $1
    print(f"[test] Sending $1 AUD to {PAYPAL_RECIPIENT_EMAIL}")
    
    result = payments.send_penalty(
        amount=1.00,
        recipient_email=PAYPAL_RECIPIENT_EMAIL,
        week_start="2025-03-01"
    )
    
    print(f"[test] Result: {result}")
    
    if result["success"]:
        print("\n✅ PAYOUT SUCCESSFUL!")
        print(f"   Payout Batch ID: {result.get('payout_batch_id')}")
        print(f"   Amount: ${result.get('amount')} AUD")
        print(f"   Recipient: {result.get('recipient')}")
        print(f"   Status: {result.get('status')}")
        
        # Check status
        print("\n[test] Checking payout status...")
        status = payments.get_payout_status(result["payout_batch_id"])
        print(f"[test] Status: {status}")
    else:
        print("\n❌ PAYOUT FAILED!")
        print(f"   Error: {result.get('error')}")
    
    return result

if __name__ == "__main__":
    test_payout()
