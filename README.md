## Advanced Bank Reconciliation

Advanced bank reconciliation for ERPNext with bulk processing capabilities.

### Features

- **Advanced Bank Reconciliation Tool**: Enhanced bank reconciliation interface with better UX
- **Bulk Reconciliation**: Process hundreds of invoices without browser timeouts
- **Real-time Progress Tracking**: Live progress updates during bulk operations
- **Automatic Batch Processing**: Smart batching to prevent database transaction issues
- **Atomic Operations**: All-or-nothing reconciliation with automatic rollback on errors
- **Background Job Support**: Long-running operations processed asynchronously
- **Custom Bank Transaction Fields**: Additional fields for better transaction management

### Bulk Reconciliation

When reconciling a bulk payment against 50+ unpaid invoices, the system automatically:

1. **Detects bulk operations** and switches to background processing
2. **Shows confirmation dialog** before starting the bulk job
3. **Displays real-time progress** with animated progress bar
4. **Processes in batches** to avoid timeouts and memory issues
5. **Sends notifications** on completion or failure
6. **Ensures data integrity** with automatic rollback on errors

**Benefits:**
- ✅ No browser freezing
- ✅ Handle 100s or 1000s of invoices
- ✅ Real-time progress visibility
- ✅ Option to run in background
- ✅ Automatic error handling

For detailed documentation, see [BULK_RECONCILIATION.md](BULK_RECONCILIATION.md)

### Installation

```bash
# Get the app
bench get-app https://github.com/yourusername/advanced_bank_reconciliation

# Install on site
bench --site your-site install-app advanced_bank_reconciliation

# Start background worker (required for bulk reconciliation)
bench worker --queue long
```

### Configuration

The bulk reconciliation feature is configured with sensible defaults:

- **Bulk Threshold**: 50 invoices (operations with 50+ invoices trigger background processing)
- **Batch Size**: 20 invoices per batch (adjustable based on server capacity)
- **Queue**: `long` queue with 1-hour timeout

To customize these settings, see [BULK_RECONCILIATION.md](BULK_RECONCILIATION.md#configuration)

### Usage

1. Navigate to **Advance Bank Reconciliation Tool**
2. Select your bank account and date range
3. Click **Get Unreconciled Entries**
4. Click **Actions** on a bank transaction
5. Select invoices to reconcile (50+ will trigger bulk mode)
6. Click Submit and confirm
7. Monitor progress in the dialog
8. Wait for completion notification

### Requirements

- Frappe Framework >= v14
- ERPNext >= v14
- Redis (for background jobs)
- SocketIO (for real-time updates)

### Documentation

- [Bulk Reconciliation Guide](BULK_RECONCILIATION.md) - Complete guide with examples
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md) - Technical details for developers
- [CHANGELOG](CHANGELOG.md) - Version history

### Support

For issues or questions:
1. Check the documentation
2. Review error logs: `bench logs`
3. Open an issue on GitHub

#### License

gpl-3.0