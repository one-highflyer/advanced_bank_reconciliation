#!/usr/bin/env python3
"""
Test script for Advanced Bank Reconciliation Background Validation

This script provides functions to test the new background validation
functionality and can be run from the console or as a scheduled task.
"""

import frappe
from frappe.utils import today, add_days
import logging

logger = frappe.logger("bank_rec_test")
logger.setLevel(logging.INFO)


def test_single_transaction_validation():
    """
    Test the validation of a single bank transaction
    """
    print("Testing single transaction validation...")
    
    # Get a sample bank transaction
    sample_transaction = frappe.db.sql("""
        SELECT bt.name 
        FROM `tabBank Transaction` bt
        INNER JOIN `tabBank Transaction Payments` btp ON bt.name = btp.parent
        WHERE bt.docstatus = 1 
        AND bt.unallocated_amount = 0.0
        LIMIT 1
    """, as_dict=True)
    
    if not sample_transaction:
        print("No suitable bank transactions found for testing")
        return False
    
    transaction_name = sample_transaction[0]['name']
    print(f"Testing with transaction: {transaction_name}")
    
    try:
        from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import validate_single_bank_transaction
        
        validate_single_bank_transaction(transaction_name)
        print("✓ Single transaction validation completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Single transaction validation failed: {str(e)}")
        return False


def test_async_validation():
    """
    Test the asynchronous validation functionality
    """
    print("Testing async validation...")
    
    # Get a sample bank transaction
    sample_transaction = frappe.db.sql("""
        SELECT bt.name 
        FROM `tabBank Transaction` bt
        INNER JOIN `tabBank Transaction Payments` btp ON bt.name = btp.parent
        WHERE bt.docstatus = 1 
        AND bt.unallocated_amount = 0.0
        LIMIT 1
    """, as_dict=True)
    
    if not sample_transaction:
        print("No suitable bank transactions found for testing")
        return False
    
    transaction_name = sample_transaction[0]['name']
    print(f"Testing async validation with transaction: {transaction_name}")
    
    try:
        from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import validate_bank_transaction_async
        
        result = validate_bank_transaction_async(transaction_name)
        
        if result.get("success"):
            print("✓ Async validation queued successfully")
            print(f"  Message: {result.get('message')}")
            return True
        else:
            print(f"✗ Async validation failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"✗ Async validation failed: {str(e)}")
        return False


def test_batch_validation():
    """
    Test batch validation functionality
    """
    print("Testing batch validation...")
    
    # Get a sample bank account
    sample_bank_account = frappe.db.sql("""
        SELECT name 
        FROM `tabBank Account` 
        WHERE is_company_account = 1
        LIMIT 1
    """, as_dict=True)
    
    if not sample_bank_account:
        print("No suitable bank accounts found for testing")
        return False
    
    bank_account = sample_bank_account[0]['name']
    print(f"Testing batch validation with bank account: {bank_account}")
    
    try:
        from advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool import batch_validate_unvalidated_transactions
        
        from_date = add_days(today(), -30)
        to_date = today()
        
        result = batch_validate_unvalidated_transactions(
            bank_account=bank_account,
            from_date=from_date,
            to_date=to_date,
            limit=10
        )
        
        if result.get("success"):
            print("✓ Batch validation completed successfully")
            print(f"  Processed: {result.get('processed_count')} transactions")
            print(f"  Total found: {result.get('total_found')} transactions")
            return True
        else:
            print(f"✗ Batch validation failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"✗ Batch validation failed: {str(e)}")
        return False




def run_all_tests():
    """
    Run all validation tests
    """
    print("=" * 60)
    print("Advanced Bank Reconciliation - Background Validation Tests")
    print("=" * 60)
    
    tests = [
        ("Single Transaction Validation", test_single_transaction_validation),
        ("Async Validation", test_async_validation),
        ("Batch Validation", test_batch_validation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All tests passed! The background validation system is working correctly.")
    else:
        print("⚠️  Some tests failed. Please review the implementation and logs.")
    
    return passed == total


def validate_system_health():
    """
    Check the overall health of the bank reconciliation system
    """
    print("\nChecking system health...")
    
    # Check if there are any bank accounts configured
    bank_accounts = frappe.db.count("Bank Account", {"is_company_account": 1})
    print(f"Bank Accounts configured: {bank_accounts}")
    
    if bank_accounts == 0:
        print("⚠️  No company bank accounts found. Please set up bank accounts first.")
        return False
    
    # Check for recent bank transactions
    recent_transactions = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabBank Transaction`
        WHERE docstatus = 1
        AND date >= %s
    """, [add_days(today(), -30)])[0][0]
    
    print(f"Recent bank transactions (last 30 days): {recent_transactions}")
    
    # Check for background job queue
    try:
        from frappe.utils.background_jobs import get_jobs
        jobs = get_jobs()
        print(f"Background jobs in queue: {len(jobs) if jobs else 0}")
    except Exception as e:
        print(f"Could not check background jobs: {str(e)}")
    
    print("✓ System health check completed")
    return True


if __name__ == "__main__":
    # This script can be run from the ERPNext console or as a scheduled task
    validate_system_health()
    run_all_tests()