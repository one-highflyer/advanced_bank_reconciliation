# Advanced Bank Reconciliation

Enhanced bank reconciliation tool for ERPNext with support for bulk operations, unpaid invoice matching, and extensible filtering.

## Features

### Core Capabilities

- **Enhanced Bank Reconciliation Interface**: Improved UX over standard ERPNext bank reconciliation
- **Unpaid Invoice Matching**: Automatically match bank transactions against unpaid Sales and Purchase Invoices
- **Invoice Returns Support**: Handle both regular invoices and returns (credit notes/debit notes) with proper sign handling
- **Bulk Reconciliation**: Process hundreds of invoices in a single operation with configurable sync/async execution
- **Real-time Progress Tracking**: Live progress updates with animated progress bar during bulk operations
- **Custom Filtering**: Extensible filter system via hooks (e.g., Customer Group filtering)
- **Date-based Filtering**: Filter matching invoices by posting date or reference date ranges
- **Extended Bank Transaction**: Custom fields and enhanced validation for bank transactions

### Bulk Reconciliation

When reconciling multiple unpaid invoices against a bank transaction:

**Configurable Execution Modes** (via Advance Bank Reconciliation Settings):
- **Background Mode** (default): Processes reconciliation asynchronously for large datasets
  - Shows real-time progress dialog with percentage completion
  - Sends desktop notifications on completion
  - Prevents browser freezing with 100s of invoices
  - Automatic batching (100 invoices per batch)

- **Synchronous Mode**: Immediate execution for small datasets
  - Instant completion with success alert
  - No progress dialog needed
  - Faster for small reconciliations

**Key Features:**
- ✅ Atomic operations with automatic rollback on errors
- ✅ Duplicate invoice detection and prevention
- ✅ Pre-validation of amounts vs outstanding balances (configurable)
- ✅ Comprehensive error logging and recovery
- ✅ WebSocket-based progress updates
- ✅ Background job monitoring with unique job IDs
- ✅ Concurrent reconciliation prevention via locking

### Invoice Returns Handling

Full support for matching returns/credit notes:

**Sales Invoices:**
- Positive outstanding → Match with deposit transactions (customer payments)
- Negative outstanding (returns) → Match with withdrawal transactions (customer refunds)

**Purchase Invoices:**
- Positive outstanding → Match with withdrawal transactions (supplier payments)
- Negative outstanding (returns) → Match with deposit transactions (supplier refunds)

**Features:**
- Absolute value matching for exact amount comparisons
- Proper payment type determination (Receive vs Pay)
- Accurate payment entry creation with correct signs

### Extensible Filtering

Add custom filters via hooks without modifying core code:

```python
# In your custom app's hooks.py
bank_rec_additional_filters = [
    {
        "dt": "Customer",  # Source doctype
        "fieldname": "customer_group",
        "fieldtype": "Link",
        "label": "Customer Group",
        "options": "Customer Group"
    },
    {
        "dt": "Customer",
        "fieldname": "territory",
        "fieldtype": "Link",
        "label": "Territory",
        "options": "Territory"
    }
]
```

The system automatically:
- Fetches related data from the specified doctype
- Applies filters to matching queries
- Updates UI with new filter fields

## Installation

```bash
# Get the app
bench get-app https://github.com/one-highflyer/advanced_bank_reconciliation

# Install on site
bench --site your-site install-app advanced_bank_reconciliation

# Migrate
bench --site your-site migrate

# Build assets
bench build --app advanced_bank_reconciliation

# Restart
bench restart

# Start background worker (required for async bulk reconciliation)
bench worker --queue long
```

## Configuration

### Advance Bank Reconciliation Settings

Navigate to **Advance Bank Reconciliation Settings** to configure:

#### Reconciling Unpaid Invoices Section

1. **Validate selection against unallocated amount** (default: unchecked)
   - When enabled: Validates that selected invoice amounts match the bank transaction's unallocated amount exactly
   - When disabled: Allows flexible selection (useful for partial reconciliations or complex scenarios)
   - Applies to both pre-validation and during processing

2. **Reconcile unpaid invoices in background** (default: checked)
   - When enabled: Runs reconciliation as a background job with progress tracking
   - When disabled: Runs reconciliation synchronously (immediate completion)
   - Recommendation: Keep enabled for operations with 10+ invoices

### Background Job Configuration

For production deployments with heavy reconciliation workload:

```bash
# In your Procfile or supervisor config
# Increase workers for the long queue
bench worker --queue long --num-workers 2
```

## Usage

### Basic Reconciliation

1. Navigate to **Advance Bank Reconciliation Tool**
2. Select your **Bank Account**
3. Set **Date Range** for bank transactions
4. Optionally enable **Filter by Reference Date** for additional date filtering
5. Click **Get Unreconciled Entries**
6. Click **Actions** button on a bank transaction row
7. Select **Match Against Voucher** in the dialog
8. Choose document types to search (Payment Entry, Journal Entry, Sales Invoice, etc.)
9. Apply filters (date range, customer group, etc.)
10. Select vouchers/invoices to reconcile
11. Click **Submit** and confirm

### Bulk Unpaid Invoice Reconciliation

For matching a single bank transaction against multiple unpaid invoices:

1. Follow steps 1-7 above
2. Enable **Unpaid Sales Invoice** or **Unpaid Purchase Invoice** checkboxes
3. Optionally apply filters:
   - **Show Only Exact Amount**: Show only invoices matching the transaction amount exactly
   - **Customer Group**: Filter by specific customer group
   - **Date filters**: Limit invoice date ranges
   - **Custom filters**: Use any custom filters added via hooks
4. Select multiple invoices (checkbox on each row or use datatable's "Select All")
5. Review the selected total shown above the table
6. Click **Submit** and confirm

**What happens next:**
- If **Background Mode** enabled:
  - Confirmation dialog appears
  - Progress dialog shows with real-time updates
  - Click "Run in Background" to minimize dialog
  - Desktop notification on completion
  - Data table refreshes automatically

- If **Synchronous Mode** enabled:
  - Confirmation dialog appears
  - Immediate processing
  - Success alert shows
  - Data table refreshes immediately

### Creating New Payment Entries

To create a new payment entry from a bank transaction:

1. Click **Actions** on a bank transaction
2. Select **Create Voucher** → **Payment Entry** or **Journal Entry**
3. Fill in required details:
   - Reference Number
   - Posting Date
   - Reference Date
   - Party Type and Party (for Payment Entry)
   - Account (for Journal Entry)
   - Mode of Payment
4. Click **Submit**

### Updating Bank Transaction Details

To update bank transaction metadata:

1. Click **Actions** on a bank transaction
2. Select **Update Bank Transaction**
3. Modify:
   - Reference Number
   - Party Type
   - Party
4. Click **Submit**

## Architecture

### Components

**Backend (Python):**
- `advance_bank_reconciliation_tool.py`: Core reconciliation logic
- `get_matching_queries()`: Dynamic query builder for matching vouchers/invoices
- `process_bulk_reconciliation()`: Background job handler with batching
- `create_payment_entry_for_invoice()`: Payment entry creation for unpaid invoices
- Extended `Bank Transaction` doctype with custom fields

**Frontend (JavaScript):**
- `dialog_manager.js`: Reconciliation dialog UI and WebSocket handling
- Real-time progress tracking via `frappe.realtime`
- Debounced row selection for performance with large datasets

**Settings:**
- `Advance Bank Reconciliation Settings`: Single doctype for global configuration

### Background Job Flow

```
User selects invoices → Pre-validation checks → Enqueue job → Background worker picks up
    ↓                                                               ↓
Returns job_id                                                  Process in batches
    ↓                                                               ↓
Frontend subscribes to events                               Send progress updates
    ↓                                                               ↓
Shows progress dialog  ←─────────────────────────────  WebSocket (frappe.publish_realtime)
    ↓                                                               ↓
Receives completion event                                   Create payment entries
    ↓                                                               ↓
Hides dialog + refreshes data  ←────────────────────────  Reconcile + commit + notify
```

### Matching Logic

The tool uses a **ranking system** to find best matches:

**Rank Score Components** (higher = better match):
- +1 if party matches
- +1 if amount matches exactly (with ABS for returns)
- +1 if currency matches
- +1 base score

**Query Types:**
- Payment Entries (paid against reference)
- Journal Entries (bank account entries)
- Sales Invoices (paid via cash/bank)
- Purchase Invoices (paid via cash/bank)
- Unpaid Sales Invoices (with returns support)
- Unpaid Purchase Invoices (with returns support)

**Exact Match Mode:**
- Uses `ABS(amount)` comparisons for returns support
- Filters only matching amounts
- Higher ranking precision

## Troubleshooting

### Progress Dialog Doesn't Close

**Symptoms:** Progress dialog stays open forever, showing 0% or partial progress

**Causes:**
1. WebSocket connection lost
2. Background worker not running
3. Job crashed without sending completion event

**Solutions:**
1. Check background worker status: `bench worker --queue long` must be running
2. Check browser console for WebSocket errors
3. Check `bench logs` for job errors
4. Try disabling "Reconcile in background" setting for immediate execution
5. Refresh the page and check if reconciliation actually completed (check bank transaction)

### Validation Errors

**"Selected allocations differ from unallocated amount":**
- Disable "Validate selection against unallocated amount" in settings if intentional
- Or adjust selections to match exactly

**"Allocated amount exceeds outstanding":**
- Indicates data inconsistency - refresh invoice data
- Check if invoice was partially paid elsewhere
- Disable validation if needed for special cases

### Performance Issues

**Slow selection with 100+ rows:**
- Already optimized with debouncing (100ms)
- Avoid using datatable inline filters (slower with large datasets)
- Use the filter fields in the dialog instead

**Timeout errors:**
- Enable background mode in settings
- Reduce batch size if needed (modify code: `batch_size = 100`)

### WebSocket Not Working

**Check:**
1. SocketIO server running: `bench serve` or production webserver config
2. Browser console for connection errors
3. Firewall/proxy allowing WebSocket connections
4. Try synchronous mode as fallback

## Development

### Adding Custom Matching Queries

Implement the hook in your custom app:

```python
# custom_app/custom_app/hooks.py
get_matching_queries = [
    "custom_app.bank_rec.get_custom_matching_queries"
]

# custom_app/custom_app/bank_rec.py
def get_custom_matching_queries(bank_account, company, transaction, document_types,
                                 from_date, to_date, filter_by_reference_date,
                                 from_reference_date, to_reference_date, exact_match):
    queries = []

    if "Custom Voucher" in document_types:
        queries.append({
            "doctype": "Custom Voucher",
            "query": get_custom_voucher_query(...),
            "filters": {...}
        })

    return queries
```

### Running Tests

```bash
# Run all tests
bench --site your-site run-tests --app advanced_bank_reconciliation

# Run specific test
bench --site your-site run-tests --app advanced_bank_reconciliation --module test_reconciliation
```

## Requirements

- **Frappe Framework**: >= v15.0.0
- **ERPNext**: >= v15.0.0
- **Python**: >= 3.10
- **Redis**: For background jobs and WebSocket
- **SocketIO**: For real-time progress updates

## License

GPL-3.0

## Support

- **Documentation**: See inline code comments and this README
- **Issues**: https://github.com/one-highflyer/advanced_bank_reconciliation/issues
- **Logs**: `bench logs` for detailed error information

## Credits

Developed by **HighFlyer** (https://highflyerglobal.com)

For ERPNext v15+ with enhanced bank reconciliation capabilities.
