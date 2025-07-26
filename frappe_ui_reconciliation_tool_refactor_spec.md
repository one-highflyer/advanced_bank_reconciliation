# Advanced Bank Reconciliation Tool – Vue 3 Refactor Specification

## 1. Objectives

1. Replace the legacy jQuery-centric implementation located at `public/js/advance_bank_reconciliation_tool/*.js` with a modern, maintainable Vue 3 codebase.
2. Preserve **all** existing server-side (Python) endpoints and business logic – the refactor is purely frontend.
3. Provide an incremental migration path so that old and new UIs can coexist during the transition.
4. Match or exceed current functionality and performance.
5. Maintain complex reconciliation workflows including unpaid invoice processing, batch validation, and async transaction processing.

---

## 2. High-Level Architecture - Vue Component Integration

**Updated Approach**: Instead of a completely standalone application, we're implementing Vue 3 components that integrate with the existing Frappe framework while maintaining the modern development experience.

```
advanced_bank_reconciliation/
├─ frontend/                    # Vue 3 components and build setup
│  ├─ src/
│  │  ├─ components/           # Vue 3 components using frappe-ui
│  │  │  ├─ TransactionsTable.vue         # Main unreconciled transactions table
│  │  │  ├─ ReconciliationDialog.vue      # Complex reconciliation workflow dialog
│  │  │  ├─ VoucherSelectionTable.vue     # Voucher matching interface
│  │  │  ├─ FiltersPanel.vue              # Date and account filters
│  │  │  ├─ NumberCards.vue               # Balance summary cards
│  │  │  └─ ActionButtons.vue             # Utility action buttons
│  │  ├─ composables/         # Vue composables wrapping frappe.call
│  │  │  ├─ useReconciliation.js          # Core reconciliation logic
│  │  │  ├─ useBankTransactions.js        # Transaction data management
│  │  │  └─ useVoucherMatching.js         # Voucher search and selection
│  │  ├─ services/            # API abstractions
│  │  │  ├─ bankReconciliation.js         # Main reconciliation APIs
│  │  │  ├─ voucherMatching.js            # Voucher search APIs
│  │  │  └─ validation.js                 # Validation APIs
│  │  ├─ utils/               # Utility functions
│  │  │  ├─ formatters.js                 # Currency, date formatting
│  │  │  ├─ constants.js                  # Document types, statuses
│  │  │  └─ helpers.js                    # Common helper functions
│  │  └─ main.js              # Component registration and exports
│  ├─ vite.config.js          # Vite configuration
│  ├─ tailwind.config.js      # TailwindCSS configuration
│  └─ package.json            # Frontend dependencies
└─ advanced_bank_reconciliation/  # Python backend (unchanged)
```

### Technology Stack
*   **Build tool:** Vite for component building and development server
*   **Language:** JavaScript + Vue 3 (Composition API with `<script setup>`)
*   **Component Library:** **frappe-ui** components (ListView, Dialog, Button, etc.)
*   **Styling:** TailwindCSS + Frappe design tokens
*   **Data table:** `ListView` component from **frappe-ui** with custom templates
*   **Dialogs:** `Dialog` component from **frappe-ui** with complex form fields
*   **State management:** Vue 3 reactivity + composables for complex workflows

### Integration Strategy
- Components are built as Vue 3 modules that can be imported into existing Frappe pages
- Maintains compatibility with Frappe's bundling system
- Uses `frappe.call()` for all server communication
- Preserves existing user permissions and authentication

---

## 3. Core Component Architecture

### TransactionsTable Component

**File**: `frontend/src/components/TransactionsTable.vue`

**Responsibilities**:
- Display unreconciled bank transactions in a `ListView` from frappe-ui
- Provide checkbox selection for bulk operations
- Individual "Reconcile" button per row that triggers reconciliation dialog
- Handle transaction state updates after reconciliation

**Key Features**:
- Column configuration: Date, Description, Reference, Amount, Actions
- Amount formatting with color coding (green for deposits, red for withdrawals)
- Row selection handling with emit events
- Loading states and empty state handling
- Responsive design for mobile devices

**Events Emitted**:
- `@reconcile` - When individual reconcile button is clicked, passes transaction data
- `@selection-change` - When row checkboxes are changed, passes selected transactions
- `@refresh` - When table data needs to be refreshed

### ReconciliationDialog Component  

**File**: `frontend/src/components/ReconciliationDialog.vue`

**Responsibilities**:
- **Primary**: Handle complex reconciliation workflows equivalent to `DialogManager` class
- Display bank transaction details in read-only form
- Provide three main action modes: Match Against Voucher, Create Voucher, Update Bank Transaction
- Handle voucher search, selection, and batch reconciliation
- Manage unpaid invoice processing with sequential workflow

**Dialog Structure**:
```
┌─ Reconciliation Dialog ────────────────────────────────────────┐
│                                                                │
│ Action: [Match Against Voucher ▼] | Document Type: [Payment ▼] │
│                                                                │
│ ┌─ Filters Section (when matching) ──────────────────────────┐ │
│ │ □ Payment Entry  □ Journal Entry  □ Unpaid Invoices       │ │
│ │ □ Exact Match    From: [date]     To: [date]              │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                │
│ ┌─ Voucher Selection Table (when matching) ──────────────────┐ │
│ │ □ Document Type | Name | Date | Amount | Reference | Party │ │
│ │ ✓ Payment Entry | PE-001 | 2024-01-15 | $1000 | REF123   │ │  
│ │ □ Unpaid Invoice| SI-001 | 2024-01-14 | $500  | INV456   │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                │
│ ┌─ Selected Summary ──────────────────────────────────────────┐ │
│ │ Total (2 selected): $1,500.00                              │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                │
│ ┌─ Bank Transaction Details ─────────────────────────────────┐ │
│ │ Date: 2024-01-15    Amount: $1,500.00                     │ │
│ │ Description: Payment received                               │ │
│ │ Allocated: $0.00    Unallocated: $1,500.00               │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                │
│                                    [Cancel] [Reconcile]        │
└────────────────────────────────────────────────────────────────┘
```

**Key Workflow States**:

1. **Match Against Voucher Mode**:
   - Shows filters for document types (Payment Entry, Journal Entry, Unpaid Invoices)
   - Displays voucher selection table with checkboxes
   - Handles mixed selection of regular vouchers and unpaid invoices
   - Shows running total of selected amounts
   - Updates allocated/unallocated amounts in real-time

2. **Create Voucher Mode**:
   - Document type selection (Payment Entry vs Journal Entry)
   - Form fields for new voucher creation (party, reference, dates, etc.)
   - Conditional fields based on document type
   - "Edit in Full Page" option to open standard Frappe forms

3. **Update Bank Transaction Mode**:
   - Form to update transaction reference, party information
   - Direct update without creating vouchers

**Complex Reconciliation Logic**:
- **Unpaid Invoice Handling**: Automatically create payment entries for unpaid invoices before reconciliation
- **Sequential Processing**: Process unpaid invoices first, then reconcile with regular vouchers
- **Auto-reconcile Logic**: When only unpaid invoices selected, auto-reconcile after payment creation
- **Mixed Processing**: Handle combinations of unpaid invoice and voucher reconciliation
- **Error Handling**: Proper rollback and error messaging for failed operations

**State Management**:
- `selectedTransaction` - Currently selected bank transaction
- `voucherFilters` - Active filters for voucher search
- `selectedVouchers` - Array of selected vouchers for reconciliation
- `actionMode` - Current dialog mode (match/create/update)
- `loadingStates` - Loading indicators for async operations

### VoucherSelectionTable Component

**File**: `frontend/src/components/VoucherSelectionTable.vue`

**Responsibilities**:
- Display matching vouchers in a selectable table format
- Handle checkbox selection with running totals
- Distinguish between voucher types (Payment Entry, Journal Entry, Unpaid Invoices)
- Provide inline filtering and sorting capabilities
- Show voucher-specific information (party, reference, amounts)

**Key Features**:
- Uses `ListView` from frappe-ui with checkbox selection
- Custom row templates for different voucher types
- Real-time total calculation for selected vouchers
- Visual indicators for unpaid invoices vs regular vouchers
- Responsive column layout

---

## 4. Integration Between Components

### TransactionsTable → ReconciliationDialog Flow

```javascript
// In parent component (main reconciliation page)
<template>
  <TransactionsTable 
    :transactions="unreconciled" 
    @reconcile="openReconciliationDialog"
  />
  
  <ReconciliationDialog
    v-model="showDialog"
    :transaction="selectedTransaction"
    @reconciled="handleReconciliationComplete"
  />
</template>

<script setup>
const showDialog = ref(false)
const selectedTransaction = ref(null)

const openReconciliationDialog = (transaction) => {
  selectedTransaction.value = transaction
  showDialog.value = true
}

const handleReconciliationComplete = (result) => {
  // Refresh transaction tables and number cards
  refreshData()
  showDialog.value = false
  frappe.show_alert(__("Bank Transaction {0} reconciled successfully", [result.transaction_name]))
}
</script>
```

### ReconciliationDialog Internal Flow

```javascript
// ReconciliationDialog.vue internal structure
<script setup>
const props = defineProps(['transaction', 'modelValue'])
const emit = defineEmits(['update:modelValue', 'reconciled'])

// Core composables for business logic
const { 
  searchVouchers, 
  reconcileVouchers, 
  createPaymentEntry,
  createJournalEntry 
} = useReconciliation()

const { 
  selectedVouchers, 
  voucherTotal, 
  handleVoucherSelection 
} = useVoucherSelection()

// Dialog state management
const actionMode = ref('Match Against Voucher')
const showVoucherTable = computed(() => actionMode.value === 'Match Against Voucher')

// Main reconciliation action
const handleReconcile = async () => {
  if (actionMode.value === 'Match Against Voucher') {
    await processVoucherMatching()
  } else if (actionMode.value === 'Create Voucher') {
    await processVoucherCreation()
  }
  emit('reconciled', { transaction_name: props.transaction.name })
}

// Complex voucher matching with unpaid invoice handling
const processVoucherMatching = async () => {
  const unpaidInvoices = selectedVouchers.value.filter(v => v.doctype.includes('Unpaid'))
  const regularVouchers = selectedVouchers.value.filter(v => !v.doctype.includes('Unpaid'))
  
  if (unpaidInvoices.length > 0) {
    // Create payment entries for unpaid invoices first
    await createPaymentEntriesForInvoices(unpaidInvoices)
  }
  
  if (regularVouchers.length > 0) {
    // Reconcile regular vouchers
    await reconcileVouchers(props.transaction.name, regularVouchers)
  }
}
</script>
```

---

## 5. API Integration & Data Flow

### Core Reconciliation APIs

The Vue components integrate with these existing server-side methods:

**Voucher Search & Matching**:
```javascript
// services/voucherMatching.js
export async function getLinkedVouchers({
  bankTransactionName,
  documentTypes,
  fromDate,
  toDate,
  exactMatch,
  filterByReferenceDate
}) {
  return frappe.call({
    method: "advanced_bank_reconciliation.advance_bank_reconciliation_tool.get_linked_payments",
    args: { bank_transaction_name: bankTransactionName, document_types: documentTypes, ... }
  })
}
```

**Reconciliation Processing**:
```javascript
// services/bankReconciliation.js
export async function reconcileVouchers(bankTransactionName, vouchers) {
  return frappe.call({
    method: "advanced_bank_reconciliation.advance_bank_reconciliation_tool.reconcile_vouchers", 
    args: { bank_transaction_name: bankTransactionName, vouchers }
  })
}

export async function createPaymentEntriesForInvoices(bankTransactionName, invoices) {
  return frappe.call({
    method: "advanced_bank_reconciliation.advance_bank_reconciliation_tool.create_payment_entries_for_invoices",
    args: { bank_transaction_name: bankTransactionName, invoices }
  })
}
```

### Composables for Business Logic

**useReconciliation Composable**:
```javascript
// composables/useReconciliation.js
export function useReconciliation() {
  const isLoading = ref(false)
  const error = ref(null)
  
  const reconcileTransaction = async (transaction, vouchers) => {
    isLoading.value = true
    try {
      // Handle complex reconciliation logic
      const unpaidInvoices = vouchers.filter(v => v.is_unpaid_invoice)
      const regularVouchers = vouchers.filter(v => !v.is_unpaid_invoice)
      
      let result = null
      if (unpaidInvoices.length > 0) {
        result = await createPaymentEntriesForInvoices(transaction.name, unpaidInvoices)
      }
      
      if (regularVouchers.length > 0) {
        result = await reconcileVouchers(transaction.name, regularVouchers)
      }
      
      return result
    } catch (err) {
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }
  
  return { reconcileTransaction, isLoading, error }
}
```

---

## 6. Complex Workflow Handling

### Unpaid Invoice Processing Workflow

The reconciliation dialog must handle the complex logic from `dialog_manager.js` for unpaid invoices:

1. **Detection Phase**:
   - Identify unpaid invoices in voucher selection (document type contains "Unpaid")
   - Separate from regular vouchers (Payment Entry, Journal Entry)

2. **Processing Phase**:
   - If unpaid invoices selected: Create payment entries first via `create_payment_entries_for_invoices`
   - If only unpaid invoices: Auto-reconcile after payment creation
   - If mixed selection: Create payments, then reconcile all vouchers together

3. **Error Handling**:
   - Rollback payment entries if reconciliation fails
   - Show specific error messages for each failure type
   - Maintain transaction state consistency

### Dialog State Transitions

```
[Open Dialog] → [Load Transaction Details] → [Show Action Selection]
     │
     ├─ [Match Against Voucher] → [Show Filters] → [Search Vouchers] → [Show Selection Table]
     │                                                   │
     │                                                   ├─ [Select Vouchers] → [Update Totals]
     │                                                   │
     │                                                   └─ [Reconcile] → [Process Mixed Types] → [Complete]
     │
     ├─ [Create Voucher] → [Show Form Fields] → [Create & Reconcile] → [Complete]
     │
     └─ [Update Transaction] → [Show Update Form] → [Update] → [Complete]
```

### Error Recovery Patterns

- **Network Failures**: Retry mechanism with exponential backoff
- **Validation Errors**: Show field-specific error messages, allow correction
- **Partial Failures**: Handle cases where some vouchers reconcile but others fail
- **State Corruption**: Reset dialog state and reload transaction data

---

## 7. Feature Parity Checklist

### Core Dialog Functionality
- [ ] **Action Mode Selection**: Match Against Voucher, Create Voucher, Update Bank Transaction
- [ ] **Document Type Filtering**: Payment Entry, Journal Entry, Unpaid Invoices checkboxes
- [ ] **Date Range Filtering**: From/To date inputs with proper validation
- [ ] **Exact Match Option**: Toggle for exact amount matching
- [ ] **Voucher Search**: Real-time search based on filter criteria

### Voucher Selection & Display
- [ ] **Voucher Table**: ListView with checkbox selection matching legacy datatable
- [ ] **Column Configuration**: Document Type, Name, Reference Date, Amount, Reference Number, Party
- [ ] **Selection Totals**: Real-time calculation and display of selected amounts
- [ ] **Mixed Type Handling**: Visual distinction between voucher types
- [ ] **Pagination**: Handle large result sets efficiently

### Reconciliation Workflows  
- [ ] **Match Against Voucher**: Complete voucher selection and reconciliation
- [ ] **Unpaid Invoice Processing**: Automatic payment entry creation workflow
- [ ] **Sequential Processing**: Unpaid invoices first, then regular vouchers
- [ ] **Auto-reconcile Logic**: When only unpaid invoices selected
- [ ] **Mixed Processing**: Combined unpaid invoice and voucher reconciliation

### Voucher Creation Workflows
- [ ] **Payment Entry Creation**: Complete form with party, reference, dates
- [ ] **Journal Entry Creation**: Entry type selection, account selection
- [ ] **Edit in Full Page**: Integration with standard Frappe forms
- [ ] **Field Validation**: Proper required field handling and validation

### Transaction Updates
- [ ] **Bank Transaction Updates**: Reference number, party type, party updates
- [ ] **Amount Allocation Tracking**: Real-time allocated/unallocated amount display
- [ ] **Currency Handling**: Proper currency formatting and calculations

### UI/UX Requirements
- [ ] **Loading States**: Progress indicators for all async operations
- [ ] **Error Handling**: User-friendly error messages and recovery options
- [ ] **Responsive Design**: Mobile-friendly dialog layout
- [ ] **Accessibility**: Keyboard navigation and screen reader support

---

## 8. Development Implementation Plan

### Phase 1: ReconciliationDialog Core Structure
- Set up basic dialog component with frappe-ui Dialog
- Implement action mode selection and conditional field display
- Add bank transaction details display (read-only section)
- Create basic form validation and error handling

### Phase 2: Voucher Matching Implementation  
- Implement voucher search with filter system
- Create VoucherSelectionTable component with ListView
- Add checkbox selection and total calculation logic
- Handle voucher type detection and visual distinction

### Phase 3: Complex Reconciliation Logic
- Implement unpaid invoice detection and processing
- Add sequential processing workflow (invoices first, then vouchers)
- Handle auto-reconcile logic for invoice-only selections
- Implement mixed voucher type reconciliation

### Phase 4: Voucher Creation Workflows
- Add Payment Entry creation form with conditional fields
- Implement Journal Entry creation with account selection
- Add "Edit in Full Page" integration with Frappe forms
- Handle voucher creation validation and error recovery

### Phase 5: Integration & Testing
- Integrate ReconciliationDialog with TransactionsTable
- Add comprehensive error handling and recovery
- Implement loading states and progress indicators
- Perform thorough testing against legacy implementation

### Phase 6: Polish & Optimization
- Add accessibility features and keyboard navigation
- Optimize performance for large datasets
- Add mobile-responsive design improvements
- Complete feature parity validation

---

## 9. Component Integration Example

### Main Reconciliation Page Structure

```vue
<!-- AdvancedBankReconciliationPage.vue -->
<template>
  <div class="reconciliation-page">
    <!-- Filters and controls -->
    <FiltersPanel 
      v-model:company="filters.company"
      v-model:bank-account="filters.bankAccount"
      v-model:date-range="filters.dateRange"
      @filter-change="refreshData"
    />
    
    <!-- Summary cards -->
    <NumberCards 
      :opening-balance="balances.opening"
      :cleared-balance="balances.cleared" 
      :difference="balances.difference"
    />
    
    <!-- Main transactions table -->
    <TransactionsTable
      :transactions="unreconciled"
      :loading="loading.transactions"
      @reconcile="openReconciliationDialog"
      @selection-change="handleBulkSelection"
    />
    
    <!-- Reconciliation dialog -->
    <ReconciliationDialog
      v-model="showReconciliationDialog"
      :transaction="selectedTransaction"
      :company="filters.company"
      :bank-account="filters.bankAccount"
      @reconciled="handleReconciliationComplete"
      @error="handleReconciliationError"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useBankTransactions } from '@/composables/useBankTransactions'
import { useBalances } from '@/composables/useBalances'

// Component imports
import FiltersPanel from '@/components/FiltersPanel.vue'
import NumberCards from '@/components/NumberCards.vue' 
import TransactionsTable from '@/components/TransactionsTable.vue'
import ReconciliationDialog from '@/components/ReconciliationDialog.vue'

// Reactive state
const filters = reactive({
  company: '',
  bankAccount: '',
  dateRange: { from: '', to: '' }
})

const showReconciliationDialog = ref(false)
const selectedTransaction = ref(null)

// Composables
const { unreconciled, loading, refreshTransactions } = useBankTransactions(filters)
const { balances, refreshBalances } = useBalances(filters)

// Event handlers
const openReconciliationDialog = (transaction) => {
  selectedTransaction.value = transaction
  showReconciliationDialog.value = true
}

const handleReconciliationComplete = async (result) => {
  // Refresh all data after successful reconciliation
  await Promise.all([
    refreshTransactions(),
    refreshBalances()
  ])
  
  showReconciliationDialog.value = false
  frappe.show_alert(__("Transaction reconciled successfully"))
}

const refreshData = async () => {
  await Promise.all([
    refreshTransactions(),
    refreshBalances()  
  ])
}

onMounted(() => {
  refreshData()
})
</script>
```

This updated specification provides a clear roadmap for implementing the ReconciliationDialog component while maintaining the complex workflow logic from the legacy implementation. The component-based approach allows for better code organization and testing while preserving all existing functionality.

---

## 10. Next Steps

1. **Implement ReconciliationDialog.vue** - Core dialog component with action modes
2. **Create VoucherSelectionTable.vue** - Voucher matching and selection interface  
3. **Integrate with TransactionsTable** - Connect reconcile button to dialog
4. **Add Composables** - Extract business logic into reusable composables
5. **Testing** - Comprehensive testing against legacy implementation
6. **Documentation** - Component documentation and usage examples

The specification now clearly defines the component architecture and integration patterns needed to build a modern Vue 3 interface that matches the complexity and functionality of the legacy jQuery implementation. 