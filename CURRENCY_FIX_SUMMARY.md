# Currency Fix Summary - Advanced Bank Reconciliation Tool

## Issues Fixed

### 1. Payment Entry Display Currency Issue

**Problem**: When reconciling a foreign currency bank account (e.g., USD) with a company base currency (e.g., LKR), the payment entry amounts were displayed in LKR instead of USD, making it difficult for users to match with USD bank transactions.

**Root Cause**: The `get_pe_matching_query` function was using `paid_amount` field which is always in the company's base currency, not the bank account's currency.

**Solution**: Modified the query to calculate amounts in the bank account's currency by:
- Using exchange rates (`source_exchange_rate` and `target_exchange_rate`) to convert base currency amounts to account currency
- For **Receive payments** (deposits): Using `received_amount / target_exchange_rate` to convert from base currency to bank account currency
- For **Pay payments** (withdrawals): Using `paid_amount / source_exchange_rate` to convert from base currency to bank account currency  
- Adding safety checks for zero division with `COALESCE` and `NULLIF`
- Adding tolerance for amount matching (0.01) to handle minor rounding differences

**Key Fix for Receive Payments**: The issue was specifically with Receive-type payment entries where the `received_amount` (stored in base currency) needed to be converted to the bank account's currency using the correct exchange rate and direction.

### 2. Cleared Balance Calculation Currency Issue

**Problem**: The `get_cleared_balance` function was calculating balances using base currency amounts instead of bank account currency amounts.

**Solution**: Updated the cleared balance query to:
- Convert payment entry amounts to bank account currency using exchange rates
- Use the same conversion logic as the matching query for consistency

## Technical Changes Made

### File: `advance_bank_reconciliation_tool.py`

#### 1. Updated `get_pe_matching_query` function (lines 811-886)
- Added currency conversion logic for multi-currency scenarios
- Modified amount comparison to use account currency amounts
- Added tolerance-based matching instead of exact matching
- Improved query to handle both base currency and foreign currency accounts

#### 2. Updated `get_cleared_balance` function (lines 1193-1226)
- Modified payment entries query to convert amounts to account currency
- Ensured consistency with the matching query logic

#### 3. Journal Entry Query (already correct)
- The `get_je_matching_query` already uses `debit_in_account_currency` and `credit_in_account_currency`
- No changes needed as Journal Entries store account currency amounts directly

## Benefits

1. **Accurate Currency Display**: Payment entries now show amounts in the bank account's currency, making reconciliation easier
2. **Consistent Matching**: Bank transactions and payment entries are now compared in the same currency
3. **Improved User Experience**: Users working with foreign currency bank accounts can easily match transactions
4. **Correct Balance Calculations**: Cleared balances are now calculated in the correct currency

## Test Scenarios

To verify the fixes work correctly, test with:
1. A USD bank account in a company with LKR base currency
2. Payment entries made in USD that should match USD bank transactions
3. Cleared balance calculations for foreign currency accounts
4. Mixed currency scenarios with both local and foreign currency transactions

## Notes

- Exchange rates are retrieved from Payment Entry fields (`source_exchange_rate`, `target_exchange_rate`)
- The solution maintains backward compatibility with single-currency setups
- Tolerance-based matching (0.01) helps handle minor rounding differences in currency conversions
- **Specific to Receive Payments**: The fix ensures that when a customer pays in USD to a USD bank account (with LKR base currency), the payment entry amount is correctly converted back to USD for bank reconciliation matching
- Added safety checks (`COALESCE` and `NULLIF`) to prevent division by zero errors with exchange rates

## Exchange Rate Logic

- **For Receive payments**: `received_amount` (base currency) ÷ `target_exchange_rate` = Bank account currency amount
- **For Pay payments**: `paid_amount` (base currency) ÷ `source_exchange_rate` = Bank account currency amount
- **Exchange rate direction**: Assumes rates are stored as conversion factors from base currency to account currency