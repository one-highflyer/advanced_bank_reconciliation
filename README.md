# Advanced Bank Reconciliation Tool - Vue 3 Frontend

A modern Vue 3 frontend for the Advanced Bank Reconciliation tool, built with frappe-ui and following the standalone application pattern.

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and Yarn installed
- Frappe development environment running
- Advanced Bank Reconciliation app installed

### Development Setup

1. **Navigate to the app directory:**
   ```bash
   cd apps/advanced_bank_reconciliation
   ```

2. **Start the Frappe development server:**
   ```bash
   bench start
   ```

3. **In another terminal, start the Vue development server:**
   ```bash
   cd apps/advanced_bank_reconciliation
   yarn dev
   ```

4. **Access the application:**
   - Open http://localhost:8080/advanced-bank-reconciliation
   - The Vue app will proxy API calls to the Frappe server on port 8000

### Production Build

```bash
cd apps/advanced_bank_reconciliation
yarn build
```

The built assets will be copied to `advanced_bank_reconciliation/public/frontend/` and served by Frappe.

## 📁 Project Structure

```
advanced_bank_reconciliation/
├─ frontend/                    # Standalone Vue app
│  ├─ src/
│  │  ├─ components/           # Reusable UI components
│  │  │  ├─ FiltersPanel.vue
│  │  │  ├─ NumberCard.vue
│  │  │  ├─ TransactionsTable.vue
│  │  │  ├─ ReconciliationDialog.vue
│  │  │  ├─ VoucherSelectionTable.vue
│  │  │  ├─ CreatePaymentEntryForm.vue
│  │  │  └─ CreateJournalEntryForm.vue
│  │  ├─ pages/               # Application pages
│  │  │  ├─ BankReconciliation.vue
│  │  │  ├─ Reports.vue
│  │  │  └─ History.vue
│  │  ├─ composables/         # Vue composables
│  │  │  ├─ useFilters.js
│  │  │  ├─ useBankReconciliation.js
│  │  │  └─ useReconciliation.js
│  │  ├─ services/            # API services
│  │  │  └─ bankReconciliation.js
│  │  ├─ utils/               # Utility functions
│  │  │  ├─ formatters.js
│  │  │  └─ currency.js
│  │  ├─ router.js            # Vue router configuration
│  │  ├─ App.vue              # Root component
│  │  └─ main.js              # App entrypoint
│  ├─ vite.config.js          # Vite configuration
│  ├─ tailwind.config.js      # TailwindCSS configuration
│  └─ package.json            # Frontend dependencies
├─ package.json               # Root workspace manager
└─ advanced_bank_reconciliation/  # Python backend (unchanged)
```

## 🛠 Technology Stack

- **Vue 3**: Composition API with `<script setup>` syntax
- **Vite**: Fast development server and optimized builds
- **frappe-ui**: Official Frappe Vue component library
- **TailwindCSS**: Utility-first styling with Frappe design tokens
- **Vue Router**: Client-side routing
- **Feather Icons**: Icon library

## 🎯 Features

### Core Functionality
- ✅ Fetch & display unreconciled transactions
- ✅ Company and Bank Account filtering
- ✅ Date range filtering (bank statement vs reference dates)
- ✅ Checkbox selection & total allocation
- ✅ Number cards with dynamic color coding

### Reconciliation Workflows
- ✅ **Match Against Voucher**: Select Payment Entries, Journal Entries, and Unpaid Invoices
- ✅ **Create Payment Entry**: New payment entry creation
- ✅ **Create Journal Entry**: New journal entry creation
- ✅ **Update Bank Transaction**: Transaction detail updates
- ✅ **Unpaid Invoice Processing**: Automatic payment entry creation
- ✅ **Sequential Processing**: Handle unpaid invoices first, then reconcile

### Validation & Processing
- ✅ **Batch Validation**: Background validation jobs with progress feedback
- ✅ **Single Transaction Validation**: Async validation with clearance date setting
- ✅ **Auto Reconcile**: Automated voucher matching
- ✅ **Error Handling**: Proper error messages and rollback

### Data Display & UI
- ✅ **Responsive Design**: Mobile-friendly interface
- ✅ **Loading States**: Progress indicators for long-running operations
- ✅ **Currency Formatting**: Proper currency display with account currency
- ✅ **Accessibility**: ARIA labels and keyboard navigation

## 🔧 Development

### Available Scripts

```bash
# Root workspace commands
yarn dev              # Start Vite dev server on port 8080
yarn build            # Build for production
yarn test             # Run tests (when implemented)
yarn lint             # ESLint + Prettier (when implemented)

# Frontend-specific commands  
cd frontend
yarn dev              # Direct Vite dev server
yarn build            # Production build
yarn preview          # Preview production build
```

### Component Development

Components are built using Vue 3 Composition API with `<script setup>` syntax:

```vue
<template>
  <div class="component">
    <!-- Template content -->
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Button, FeatherIcon } from 'frappe-ui'

// Component logic
const props = defineProps({
  // Props definition
})

const emit = defineEmits([
  // Events definition
])

// Reactive state and computed properties
</script>
```

### API Integration

All backend calls are made through the `frappe.call()` function:

```javascript
// services/bankReconciliation.js
export async function getUnreconciledTransactions(filters = {}) {
  return frappe.call({
    method: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.get_unreconciled_transactions',
    args: filters
  }).then(r => r.message || [])
}
```

### State Management

State is managed using Vue 3 composables:

```javascript
// composables/useBankReconciliation.js
export function useBankReconciliation() {
  const transactions = ref([])
  const loading = ref(false)
  
  const getUnreconciledEntries = async (filters = {}) => {
    // Implementation
  }
  
  return {
    transactions,
    loading,
    getUnreconciledEntries
  }
}
```

## 🎨 Styling

The application uses TailwindCSS with Frappe design tokens:

- **Colors**: Frappe color palette (blue, green, red, yellow, gray)
- **Typography**: Frappe font stack and sizing
- **Spacing**: Consistent spacing scale
- **Components**: frappe-ui components for consistency

## 📱 Responsive Design

The interface is fully responsive with breakpoints:
- **Mobile**: < 768px
- **Tablet**: 768px - 1024px  
- **Desktop**: > 1024px

## 🔒 Security

- **Authentication**: Inherits Frappe session authentication
- **Permissions**: Respects Frappe user permissions and roles
- **CSRF Protection**: Handled automatically by frappe-ui-starter setup
- **API Validation**: All API calls validated on backend

## 🧪 Testing

Testing strategy (to be implemented):
- **Unit Tests**: Vue components with `@vue/test-utils`
- **Integration Tests**: API service layer with mocked responses
- **E2E Tests**: Complete reconciliation workflows

## 🚀 Deployment

### Development
1. Start Frappe server: `bench start`
2. Start Vue dev server: `yarn dev`
3. Access at: http://localhost:8080/advanced-bank-reconciliation

### Production
1. Build frontend: `yarn build`
2. Assets copied to: `advanced_bank_reconciliation/public/frontend/`
3. Served by Frappe at: `/advanced-bank-reconciliation`

## 🔄 Migration Strategy

The implementation follows an incremental migration approach:

1. **Phase 0**: Vue frontend created alongside existing implementation
2. **Phase 1**: Development and testing of Vue app
3. **Phase 2**: Navigation links added to standalone app
4. **Phase 3**: Vue app becomes primary interface
5. **Phase 4**: Legacy JS implementation removed

## 🤝 Contributing

1. Follow Vue 3 Composition API patterns
2. Use frappe-ui components when available
3. Maintain responsive design principles
4. Add proper error handling and loading states
5. Follow the established file structure

## 📄 License

This project is part of the Advanced Bank Reconciliation app and follows the same license terms.

## 🆘 Support

For issues and questions:
1. Check the Frappe documentation
2. Review the frappe-ui component library
3. Consult the Vue 3 documentation
4. Open an issue in the project repository

---

*Built with ❤️ using Vue 3, frappe-ui, and TailwindCSS*