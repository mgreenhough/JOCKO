#!/usr/bin/env python3
"""
ACTUAL PENALTY EXECUTION TEST

This script executes the REAL penalty mechanism using the EXACT same code path
as the production scheduler. It will transfer REAL money if in live mode.

Usage:
    # Test with sandbox (recommended first)
    python test_penalty_execution.py --sandbox
    
    # Live test with small amount (after confirming sandbox works)
    python test_penalty_execution.py --live --amount 1.00

WARNING: --live will transfer REAL money from your PayPal account!
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database
import payments
import coach
import config


def main():
    parser = argparse.ArgumentParser(description="Execute actual penalty test")
    parser.add_argument("--sandbox", action="store_true", help="Use PayPal sandbox")
    parser.add_argument("--live", action="store_true", help="Use PayPal live (REAL MONEY)")
    parser.add_argument("--amount", type=float, default=1.00, help="Penalty amount (default: $1.00)")
    parser.add_argument("--recipient", help="Override recipient email")
    args = parser.parse_args()

    if not args.sandbox and not args.live:
        print("Error: Must specify --sandbox or --live")
        sys.exit(1)

    # Initialize
    database.init_db()
    
    # Set mode
    if args.sandbox:
        payments.set_mode("sandbox")
        print("✓ Sandbox mode enabled")
    else:
        print("⚠️  LIVE MODE - REAL MONEY WILL BE TRANSFERRED")
        print(f"   Amount: ${args.amount:.2f} AUD")

    # Get parameters
    week_start = coach._get_week_start(0)
    recipient = args.recipient or database.get_setting("recipient_email") or config.PAYPAL_RECIPIENT_EMAIL
    amount = args.amount

    print(f"\nPenalty Parameters:")
    print(f"  Mode: {payments.PAYPAL_MODE}")
    print(f"  Amount: ${amount:.2f} AUD")
    print(f"  Recipient: {recipient}")
    print(f"  Week: {week_start}")

    # Confirm for live mode
    if args.live:
        confirm = input("\nType 'EXECUTE' to confirm real penalty execution: ")
        if confirm != "EXECUTE":
            print("Cancelled.")
            sys.exit(0)

    # THIS IS THE EXACT CALL from scheduler.py lines 348-352
    print(f"\nExecuting payments.send_penalty()...")
    result = payments.send_penalty(
        amount=amount,
        recipient_email=recipient,
        week_start=week_start
    )

    # Handle result (same as scheduler.py lines 354-414)
    print(f"\nResult:")
    print(f"  Success: {result.get('success')}")
    
    if result.get('success'):
        print(f"  Payout Batch ID: {result.get('payout_batch_id')}")
        print(f"  Status: {result.get('status')}")
        print(f"\n✓ PENALTY EXECUTED SUCCESSFULLY")
        
        # Log to database (same as scheduler.py lines 380-389)
        compliance = coach.check_goal_compliance()
        database.log_penalty(
            week_start=week_start,
            goal_workouts=compliance["goals"]["workouts_per_week"],
            actual_workouts=compliance["current"]["session_count"],
            goal_sprints=compliance["goals"]["sprints_per_week"],
            actual_sprints=compliance["current"]["sprint_count"],
            penalty_amount=amount,
            paid=1,
            recipient_email=recipient
        )
        print("✓ Penalty logged to database")
        
    else:
        print(f"  Error: {result.get('error')}")
        if result.get('insufficient_funds'):
            print("\n✗ FAILED: Insufficient funds")
        else:
            print("\n✗ FAILED: Payout error")


if __name__ == "__main__":
    main()