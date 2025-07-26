# Advanced Bank Reconciliation Tool – Vue 3 Refactor Specification

## 1. Objectives

1. Replace the legacy jQuery-centric implementation located at `public/js/advance_bank_reconciliation_tool/*.js` with a modern, maintainable Vue 3 codebase.
2. Preserve **all** existing server-side (Python) endpoints and business logic – the refactor is purely frontend.
3. Provide an incremental migration path so that old and new UIs can coexist during the transition.
4. Match or exceed current functionality and performance.
5. Maintain complex reconciliation workflows including unpaid invoice processing, batch validation, and async transaction processing.

---

## 2. High-Level Architecture - Standalone Vue Application

Following the **helpdesk app pattern**, create a standalone Vue application outside the Frappe desk:

```
advanced_bank_reconciliation/
├─ frontend/                    # Standalone Vue app (frappe-ui-starter)
│  ├─ src/
│  │  ├─ components/           # Reusable UI widgets
│  │  ├─ pages/               # Application pages/views
│  │  ├─ composables/         # Vue composables wrapping frappe.call
│  │  ├─ services/            # API abstractions (bank reconciliation endpoints)
│  │  ├─ stores/              # Pinia stores for state management
│  │  ├─ utils/               # Utility functions (currency, dates, etc.)
│  │  ├─ router/              # Vue router configuration
│  │  ├─ App.vue              # Root component
│  │  └─ main.js              # App entrypoint
│  ├─ public/                 # Static assets
│  ├─ vite.config.js          # Vite configuration with Frappe proxy
│  ├─ tailwind.config.js      # TailwindCSS configuration
│  ├─ package.json            # Frontend dependencies
│  └─ index.html              # Entry HTML
├─ package.json               # Root workspace manager (like helpdesk)
└─ advanced_bank_reconciliation/  # Python backend (unchanged)
```

### Technology Stack
*   **Build tool:** Vite (fast, tree-shaking, matches frappe-ui-starter).
*   **Language:** JavaScript/TypeScript + Vue 3 (Composition API).
*   **Component Library:** **frappe-ui** (official Frappe Vue components).
*   **Styling:** TailwindCSS + Frappe design tokens.
*   **Data table:** Use `Table` component from **frappe-ui** with extensions as needed.
*   **Charts & cards:** Leverage `frappe-ui` components (`NumberCard`, `Chart`).
*   **State management:** Pinia stores for complex state, Vue 3 reactivity for component state.
*   **Routing:** Vue Router for SPA navigation.

### Benefits of Standalone Architecture
- **Independent Development**: Frontend can be developed/deployed separately
- **Modern Tooling**: Full Vite dev server with HMR
- **Clean Separation**: Clear API boundary between frontend and backend
- **Scalability**: Easier to scale frontend independently
- **Reusability**: Components can be shared across other apps

---

## 3. Application Setup & Integration

### Initial Setup using frappe-ui-starter

```bash
cd apps/advanced_bank_reconciliation
npx degit netchampfaris/frappe-ui-starter frontend
cd frontend
yarn install
```

### Root Workspace Configuration

Create `package.json` in app root (following helpdesk pattern):
```json
{
  "private": true,
  "scripts": {
    "dev": "cd frontend && yarn dev",
    "build": "cd frontend && yarn build"
  },
  "workspaces": ["frontend"]
}
```

### Frontend Application Routes

The standalone app will be served at `/advanced-bank-reconciliation` with routes:
- `/advanced-bank-reconciliation/` - Main reconciliation tool
- `/advanced-bank-reconciliation/reports` - Reconciliation reports  
- `/advanced-bank-reconciliation/history` - Transaction history

### Integration with Frappe Backend

1. **API Communication**: All backend calls via `frappe.call()` from the Vue app
2. **Authentication**: Inherits Frappe session authentication  
3. **Permissions**: Respects Frappe user permissions and roles
4. **CSRF Protection**: Handled automatically by frappe-ui-starter setup

### Development Workflow

```bash
# Start Frappe development server
bench start

# In another terminal, start Vue dev server
cd apps/advanced_bank_reconciliation
yarn dev
```

The Vue app runs on port 8080 and proxies API calls to the Frappe server on port 8000.

### Production Deployment

```bash
# Build the frontend
cd apps/advanced_bank_reconciliation
yarn build

# Assets are copied to advanced_bank_reconciliation/public/frontend/
# Served by Frappe at /advanced-bank-reconciliation
```

### Access from Frappe Desk

Add navigation link in the app's desk/workspace configuration or create a custom button that opens the standalone app in a new tab/window.

---

## 4. Core Vue Components

| Component | Responsibility |
|-----------|----------------|
| `AdvanceBankReconciliationPage` | Top-level page, holds filters, renders statistics cards, tables and actions. |
| `FiltersPanel` | Company, Bank Account, Date range, Reference date toggles. |
| `NumberCards` | Summary cards (opening balance, cleared balance, difference) with dynamic color coding. |
| `TransactionsTable` | Unreconciled transactions – rendered with `frappe-ui` Table with checkbox selection. |
| `ReconciledTransactionsTable` | Already reconciled list (toggle view). |
| `ReconciliationDialog` | Complex Match/Create/Update workflow; mirrors legacy `DialogManager` with unpaid invoice handling. |
| `VoucherSelectionTable` | Nested table in dialog for voucher selection with payment/invoice distinction. |
| `UploadStatementButton` | Opens standard Frappe upload flow via `frappe.call`. |
| `BatchValidationButton` | Triggers server-side validation jobs with progress feedback. |
| `AutoReconcileButton` | Automated voucher matching functionality. |
| `ChartSection` | Balance river chart – re-use existing chart config. |
| `ActionButtons` | Get Unreconciled Entries, validation actions, etc. |

Each component lives in its own folder with a `.vue` file (SFC), optional scoped CSS, and tests.

---

## 5. API Endpoints Integration

The Vue frontend must integrate with these existing server-side methods:

### Core Reconciliation APIs
- `advanced_bank_reconciliation.advance_bank_reconciliation_tool.get_linked_payments` - Get vouchers matching bank transaction
- `advanced_bank_reconciliation.advance_bank_reconciliation_tool.reconcile_vouchers` - Match selected vouchers with bank transaction
- `advanced_bank_reconciliation.advance_bank_reconciliation_tool.create_payment_entries_for_invoices` - Create payment entries for unpaid invoices
- `advanced_bank_reconciliation.advance_bank_reconciliation_tool.create_payment_entry_bts` - Create new payment entry
- `advanced_bank_reconciliation.advance_bank_reconciliation_tool.create_journal_entry_bts` - Create new journal entry

### Validation & Processing APIs
- `advanced_bank_reconciliation.advance_bank_reconciliation_tool.validate_bank_transactions` - Validate transactions in date range
- `advanced_bank_reconciliation.advance_bank_reconciliation_tool.batch_validate_unvalidated_transactions` - Batch validation with progress tracking
- `advanced_bank_reconciliation.advance_bank_reconciliation_tool.validate_bank_transaction_async` - Single transaction async validation

### Data Retrieval APIs
- `erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_account_balance` - Account balances
- `erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.auto_reconcile_vouchers` - Automated matching
- `erpnext.accounts.doctype.bank_statement_import.bank_statement_import.upload_bank_statement` - Statement upload
- `frappe.client.get_value` - Bank transaction details

## 6. Data Flow & Services

1. **API layer** (`/services`)
   * `bankReconciliation.api.ts` exports functions that wrap `frappe.call` with `async/await`:
     ```ts
     export async function getLinkedVouchers(args: GetLinkedVoucherArgs) {
       return frappe.call<{ message: VoucherRaw[] }>({
         method: "advanced_bank_reconciliation.advance_bank_reconciliation_tool.get_linked_payments",
         args,
       }).then(r => r.message);
     }
     
     export async function reconcileVouchers(bankTransactionName: string, vouchers: VoucherItem[]) {
       return frappe.call({
         method: "advanced_bank_reconciliation.advance_bank_reconciliation_tool.reconcile_vouchers",
         args: { bank_transaction_name: bankTransactionName, vouchers },
       });
     }
     ```
2. **Composables**
   * `useVouchers`, `useBankTransactions`, `useNumberCards`, `useValidation` abstract server calls and provide reactive state + loading/error to components.
3. **Store (optional)**
   * A Pinia store (e.g., `useReconciliationStore`) can keep globally selected bank account, date filters, and shared mutations.

---

## 7. Feature Parity Checklist

### Core Functionality
- [ ] Fetch & display unreconciled transactions with identical filters (bank statement dates vs reference dates).
- [ ] Checkbox selection & total allocator identical to `show_selected_transactions`.
- [ ] Company and Bank Account filtering with proper query filters.
- [ ] Date range filtering (bank statement dates and reference dates with toggle).

### Reconciliation Workflows
- [ ] **Match Against Voucher**: Complex selection of Payment Entries, Journal Entries, and Unpaid Invoices.
- [ ] **Create Payment Entry**: New payment entry creation with proper bank account linking.
- [ ] **Create Journal Entry**: New journal entry creation workflow.
- [ ] **Update Bank Transaction**: Transaction detail updates.
- [ ] **Unpaid Invoice Processing**: Automatic payment entry creation for invoices before reconciliation.
- [ ] **Sequential Processing**: Handle unpaid invoices first, then reconcile with regular vouchers.

### Validation & Processing
- [ ] **Batch Validation**: Queue background validation jobs with progress feedback.
- [ ] **Single Transaction Validation**: Async validation with proper clearance date setting.
- [ ] **Auto Reconcile**: Automated voucher matching functionality.
- [ ] **Error Handling**: Proper error messages and rollback handling.

### Data Display & UI
- [ ] **Number Cards**: Opening balance, cleared balance, difference with dynamic color coding.
- [ ] **Reconciled Transactions Toggle**: Show/hide already reconciled transactions.
- [ ] **Upload Statement**: Integration with Frappe's bank statement import.
- [ ] **Currency Formatting**: Proper currency display with account currency.
- [ ] **Loading States**: Progress indicators for long-running operations.

### Technical Requirements
- [ ] **i18n Support**: All user-facing text using `__()` helper.
- [ ] **Responsive Design**: Mobile-friendly interface.
- [ ] **Accessibility**: Proper ARIA labels and keyboard navigation.
- [ ] **Error Boundaries**: Graceful error handling and recovery.

---

## 7. Complex Workflow Considerations

### Unpaid Invoice Handling
The current implementation has sophisticated logic for handling unpaid invoices that must be preserved:
1. **Detection**: Distinguish between regular vouchers and unpaid invoices in voucher selection.
2. **Sequential Processing**: Create payment entries for unpaid invoices first, then reconcile.
3. **Auto-reconcile Logic**: When only unpaid invoices are selected, auto-reconcile after payment creation.
4. **Combined Processing**: When both unpaid invoices and regular vouchers are selected, create payments first, then reconcile all together.

### State Management Complexity
- **Inter-component Communication**: Dialog updates must refresh parent table data and number cards.
- **Transaction State**: Track allocated/unallocated amounts across multiple voucher selections.
- **Validation State**: Handle async validation job status and progress updates.
- **Filter State**: Maintain filter settings across component interactions.

### Bundle Loading Strategy
- **Compatibility**: Maintain existing `frappe.require("advance-bank-reconciliation-tool.bundle.js")` pattern.
- **Feature Flagging**: Use configuration-based switching between Vue and legacy implementations.

---

## 8. Incremental Migration Strategy

1. **Phase-0:** Create the standalone Vue frontend using frappe-ui-starter but don't expose routes yet.
2. **Phase-1:** Develop and test the Vue app alongside existing doctype form. Access via direct URL for testing.
3. **Phase-2:** Add navigation links in Frappe desk to the standalone app. Both implementations available.
4. **Phase-3:** Make standalone app the primary interface. Update documentation and user training.
5. **Phase-4:** Remove legacy JS implementation and old doctype form fields.

### Migration Benefits with Standalone Approach
- **Zero Disruption**: Existing workflow remains untouched during development
- **Easy Rollback**: Old implementation stays functional as fallback
- **Gradual Adoption**: Users can choose between old and new interfaces during transition
- **Independent Testing**: Vue app can be thoroughly tested without affecting current users

### Migration Safety Measures
- **API Compatibility**: Ensure all existing API contracts remain unchanged.
- **Data Validation**: Compare Vue output with legacy implementation during parallel testing.
- **Rollback Plan**: Quick switching mechanism between Vue and legacy implementations.

---

## 9. Tooling & Developer Experience

### Development Commands

```bash
# Root workspace commands
cd apps/advanced_bank_reconciliation
yarn dev              # Start Vite dev server on port 8080
yarn build            # Build for production

# Frontend-specific commands  
cd apps/advanced_bank_reconciliation/frontend
yarn dev              # Direct Vite dev server
yarn build            # Production build
yarn test             # Run tests
yarn lint             # ESLint + Prettier
```

### Development Stack
* **Vite**: Fast dev server with HMR, optimized builds
* **Vue 3**: Composition API with `<script setup>` syntax
* **TypeScript**: Optional, can start with JavaScript and migrate gradually
* **ESLint + Prettier**: Code formatting and quality
* **Vitest + @vue/test-utils**: Unit and component testing
* **TailwindCSS**: Utility-first styling with Frappe design tokens
* **frappe-ui**: Official component library with consistent design

### IDE Setup
* **VS Code**: Recommended with Volar extension for Vue 3
* **Vue DevTools**: Browser extension for debugging
* **TypeScript**: IntelliSense and type checking

---

## 10. Milestones & Timeline

| Milestone | Deliverable | ETA |
|-----------|-------------|-----|
| 1 | Scaffold `frontend/`, Vite, Hello World page | **Week 1** |
| 2 | Implement FiltersPanel + API services | **Week 2** |
| 3 | TransactionsTable (read-only) | **Week 3** |
| 4 | ReconciliationDialog (Match flow) | **Week 4–5** |
| 5 | Create/Update Voucher flows & unpaid invoice handling | **Week 6** |
| 6 | Validation workflows & batch processing | **Week 7** |
| 7 | Charts & NumberCards | **Week 8** |
| 8 | Parity QA & bug-fix, enable feature flag | **Week 9** |
| 9 | Remove legacy JS (Phase-3) | **Week 11** |

---

## 11. Open Questions & Considerations

1. **Component Library**: What additional `frappe-ui` Vue components can we adopt to reduce custom code (e.g., Modal, DateRangePicker)?
2. **Accessibility**: What are the specific accessibility requirements for keyboard navigation and screen readers?
3. **Mobile Responsiveness**: Should the tool have a mobile-optimized interface or remain desktop-only?
4. **Performance**: How to handle large datasets (>1000 transactions) efficiently in the Vue table component?
5. **Testing Strategy**: What level of integration testing is needed for the complex reconciliation workflows?
6. **Browser Support**: Which browsers and versions need to be supported?

---

## 12. Testing Strategy

### Unit Testing
- **Component Tests**: Vue components with `@vue/test-utils` and Vitest
- **Service Tests**: API service layer with mocked `frappe.call` responses
- **Composable Tests**: Vue composables with proper reactive state testing

### Integration Testing
- **Workflow Tests**: End-to-end reconciliation workflows with real API responses
- **State Management**: Cross-component state updates and communication
- **Error Handling**: Network failures, validation errors, and recovery

### Regression Testing
- **Parallel Testing**: Run Vue and legacy implementations side-by-side during transition
- **Data Validation**: Compare outputs to ensure identical results
- **Performance Testing**: Ensure Vue implementation matches or exceeds legacy performance

### Manual Testing Scenarios
1. **Complex Reconciliation**: Mixed voucher types including unpaid invoices
2. **Batch Validation**: Large datasets with progress tracking
3. **Error Recovery**: Network interruptions during reconciliation
4. **State Persistence**: Filter settings and selection state across interactions

---

## 13. References

* Legacy implementation: `public/js/advance_bank_reconciliation_tool/dialog_manager.js` & `doctype/advance_bank_reconciliation_tool/*.js`.
* Similar Vue migration: `woodsmiths_erp_app/page/work_order_creator/work_order_creator.js`.
* Frappe Vue guide: https://frappeframework.com/docs/user/en/front-end/vue
* Current API endpoints: `advanced_bank_reconciliation/doctype/advance_bank_reconciliation_tool/advance_bank_reconciliation_tool.py`

---

---

## 14. Quick Start Guide

### Prerequisites
- Node.js 18+ and Yarn installed
- Frappe development environment running
- Advanced Bank Reconciliation app installed

### Setup Steps

```bash
# 1. Navigate to the app directory
cd apps/advanced_bank_reconciliation

# 2. Initialize the frontend using frappe-ui-starter
npx degit netchampfaris/frappe-ui-starter frontend

# 3. Create root workspace package.json
cat > package.json << 'EOF'
{
  "private": true,
  "scripts": {
    "dev": "cd frontend && yarn dev",
    "build": "cd frontend && yarn build"
  },
  "workspaces": ["frontend"]
}
EOF

# 4. Install dependencies
cd frontend
yarn install

# 5. Configure development site (in site_config.json)
echo '{"ignore_csrf": 1}' >> sites/yoursite/site_config.json

# 6. Start development
bench start  # In one terminal
yarn dev     # In another terminal (from frontend/)

# 7. Access the app
# Open http://yoursite.localhost:8080/advanced-bank-reconciliation
```

### Next Steps
1. Configure routes in `frontend/src/router/index.js`
2. Set up API services in `frontend/src/services/`
3. Create page components in `frontend/src/pages/`
4. Implement reconciliation workflows

---

## 15. Standalone Application Benefits

### Developer Experience
- **Modern Tooling**: Full Vite dev server with instant HMR and optimized builds
- **Independent Development**: Frontend team can work without backend dependencies
- **Component Isolation**: Easy to test and develop components in isolation
- **Hot Module Replacement**: Instant feedback during development

### Architecture Benefits  
- **Clean Separation**: Clear API boundaries between frontend and backend
- **Scalability**: Easier to scale frontend and backend independently
- **Deployment Flexibility**: Can deploy frontend to CDN or separate infrastructure
- **Technology Independence**: Frontend can evolve independently of Frappe core

### User Experience
- **Performance**: Optimized SPA with code splitting and lazy loading
- **Responsiveness**: Modern SPA interactions and smooth transitions
- **Offline Capability**: Potential for service worker and offline functionality
- **Mobile-First**: Better mobile experience with responsive design

### Maintenance Benefits
- **Version Control**: Cleaner git history with separated concerns
- **Testing**: Easier unit testing and component testing
- **Debugging**: Better dev tools and debugging experience
- **Documentation**: Component documentation with Storybook/Histoire

---

*Document generated and updated based on current implementation analysis. Updated to use standalone Vue application approach with frappe-ui-starter template following the helpdesk app pattern. Feel free to amend as requirements evolve.* 