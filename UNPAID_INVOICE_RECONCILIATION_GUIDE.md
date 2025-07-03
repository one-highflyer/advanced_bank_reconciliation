# Unpaid Invoice Reconciliation - User Guide

## Overview

The Advanced Bank Reconciliation Tool now supports direct reconciliation of bank transactions against unpaid Sales and Purchase invoices. This feature automatically creates payment entries during the reconciliation process, eliminating the need for manual payment entry creation.

## When to Use This Feature

Use this feature when:
- You have bank transactions for payments received/made
- The corresponding invoices exist in ERPNext but are still marked as unpaid
- No payment entries have been created for these invoices yet
- You want to reconcile the bank transaction and mark the invoice as paid in one step

## Step-by-Step Guide

### 1. Access the Bank Reconciliation Tool

1. Navigate to **Advanced Bank Reconciliation Tool**
2. Select your **Company** and **Bank Account**
3. Set the appropriate date range
4. Click **Get Unreconciled Entries**

### 2. Select a Bank Transaction

1. From the unreconciled transactions list, click on the transaction you want to reconcile
2. Click the **Actions** button and select **Match Against Voucher**

### 3. Configure Reconciliation Options

1. In the reconciliation dialog, you'll see various document type options
2. **New Options Available:**
   - ✅ **Unpaid Sales Invoice** - for incoming payments
   - ✅ **Unpaid Purchase Invoice** - for outgoing payments
3. Select the appropriate option(s) based on your transaction type:
   - For **deposits/credits**: Select "Unpaid Sales Invoice"
   - For **withdrawals/debits**: Select "Unpaid Purchase Invoice"

### 4. Review Matching Invoices

1. The system will display unpaid invoices that match your transaction
2. Invoices are ranked by relevance (party match, amount match, etc.)
3. You can see:
   - **Invoice Number**
   - **Customer/Supplier**
   - **Outstanding Amount**
   - **Posting Date**

### 5. Select Invoices for Reconciliation

1. Use the checkboxes to select one or more invoices
2. The system shows the total selected amount
3. You can select multiple invoices if the bank transaction covers several invoices
4. **Partial Payments:** The system supports partial payments if the bank amount is less than the invoice amount

### 6. Complete the Reconciliation

1. Click **Submit** to process the reconciliation
2. The system will automatically:
   - Create payment entries for each selected invoice
   - Link the payment entries to the invoices
   - Update the invoice status to "Paid" (or "Partly Paid" for partial payments)
   - Reconcile the payment entries with the bank transaction
   - Update the bank transaction status to "Reconciled"

### 7. Confirmation

1. You'll receive a success message: "Payment Entries created and Bank Transaction [ID] Matched"
2. The reconciled transaction moves to the "Matched Transactions" section
3. You can view the created payment entries in the Accounts module

## Example Scenarios

### Scenario 1: Customer Payment Received

**Situation:** 
- Customer ABC Ltd paid $1,000 via bank transfer
- Sales Invoice SINV-2024-001 for $1,000 exists but is unpaid
- Bank shows $1,000 deposit

**Steps:**
1. Select the $1,000 deposit transaction
2. Choose "Match Against Voucher"
3. Check "Unpaid Sales Invoice"
4. Select SINV-2024-001 from the list
5. Submit

**Result:**
- Payment Entry created linking bank account and customer
- Sales Invoice SINV-2024-001 marked as "Paid"
- Bank transaction reconciled

### Scenario 2: Supplier Payment Made

**Situation:**
- Paid supplier XYZ Corp $500 via bank transfer
- Purchase Invoice PINV-2024-001 for $500 exists but is unpaid
- Bank shows $500 withdrawal

**Steps:**
1. Select the $500 withdrawal transaction
2. Choose "Match Against Voucher"
3. Check "Unpaid Purchase Invoice"
4. Select PINV-2024-001 from the list
5. Submit

**Result:**
- Payment Entry created linking bank account and supplier
- Purchase Invoice PINV-2024-001 marked as "Paid"
- Bank transaction reconciled

### Scenario 3: Partial Payment

**Situation:**
- Customer paid $300 against a $500 invoice
- Bank shows $300 deposit

**Steps:**
1. Select the $300 deposit transaction
2. Choose "Match Against Voucher"
3. Check "Unpaid Sales Invoice"
4. Select the $500 invoice from the list
5. Submit

**Result:**
- Payment Entry created for $300
- Invoice marked as "Partly Paid" with $200 outstanding
- Bank transaction reconciled

## Benefits

- **Time Saving:** No need to manually create payment entries
- **Error Reduction:** Automatic creation ensures data consistency
- **Audit Trail:** Clear linkage between bank transactions, payments, and invoices
- **Batch Processing:** Handle multiple invoices in one reconciliation
- **Flexibility:** Support for partial payments

## Important Notes

1. **Permissions:** You need appropriate permissions to create Payment Entries
2. **Outstanding Amount:** Only invoices with outstanding amounts > 0 will appear
3. **Invoice Status:** Only submitted invoices that are not paid/cancelled will be shown
4. **Currency:** Ensure invoice and bank transaction currencies match
5. **Date Validation:** Payment entry date will be set to the bank transaction date

## Troubleshooting

### Issue: No unpaid invoices showing up
**Possible Causes:**
- All invoices are already paid
- Invoice amounts don't match the bank transaction amount (try unchecking "Show Only Exact Amount")
- Date range is too restrictive
- Wrong party (customer/supplier) in the bank transaction

### Issue: Payment entry creation fails
**Possible Causes:**
- Insufficient permissions
- Currency mismatch between invoice and bank account
- Invalid bank account configuration
- Invoice already has partial payments that would exceed the total

### Issue: Cannot find the option
**Possible Causes:**
- Feature not enabled in your system
- Using wrong transaction type (check if deposit/withdrawal)
- Bank account not properly configured

## Related Topics

- Bank Reconciliation Statement
- Payment Entry
- Sales Invoice
- Purchase Invoice
- Payment Reconciliation

For additional support, contact your system administrator or refer to the ERPNext documentation.