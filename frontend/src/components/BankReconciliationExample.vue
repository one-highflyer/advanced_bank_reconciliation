<template>
  <div class="bank-reconciliation-example p-6 max-w-7xl mx-auto">
    <div class="mb-6">
      <h2 class="text-2xl font-bold text-gray-900 mb-2">Bank Reconciliation Tool</h2>
      <p class="text-gray-600">Select a transaction and click "Reconcile" to start the reconciliation process.</p>
    </div>

    <!-- Sample Transaction Data for Demo -->
    <div class="mb-6 p-4 bg-blue-50 rounded-lg">
      <h3 class="text-lg font-medium text-blue-900 mb-2">Demo Instructions</h3>
      <p class="text-blue-700 text-sm">
        This example shows how the TransactionsTable and ReconciliationDialog work together.
        Click the "Reconcile" button on any transaction to open the reconciliation dialog.
      </p>
    </div>

    <!-- Transactions Table -->
    <div class="mb-6">
      <h3 class="text-lg font-medium text-gray-900 mb-4">Unreconciled Transactions</h3>
      <TransactionsTable
        :transactions="sampleTransactions"
        :loading="loading"
        @reconcile="handleReconcileClick"
        @selection-change="handleSelectionChange"
      />
    </div>

    <!-- Reconciliation Dialog -->
    <ReconciliationDialog
      v-model="showReconciliationDialog"
      :transaction="selectedTransaction"
      :company="selectedCompany"
      :bank-account="selectedBankAccount"
      @reconciled="handleReconciliationComplete"
      @error="handleReconciliationError"
    />

    <!-- Status Messages -->
    <div v-if="statusMessage" class="mt-4 p-4 rounded-lg" :class="statusMessageClass">
      {{ statusMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import TransactionsTable from './TransactionsTable.vue'
import ReconciliationDialog from './ReconciliationDialog.vue'

// Demo state
const loading = ref(false)
const showReconciliationDialog = ref(false)
const selectedTransaction = ref(null)
const selectedCompany = ref('Sample Company Ltd')
const selectedBankAccount = ref('HDFC Bank - 12345')
const statusMessage = ref('')
const statusMessageClass = ref('')

// Sample transaction data for demonstration
const sampleTransactions = ref([
  {
    name: 'BT-2024-00001',
    date: '2024-01-15',
    description: 'ONLINE TRANSFER FROM ACME CORP',
    reference_number: 'TXN123456',
    deposit: 15000.00,
    withdrawal: 0,
    currency: 'USD',
    allocated_amount: 0,
    unallocated_amount: 15000.00,
    party_type: null,
    party: null,
    bank_account: 'HDFC Bank - 12345',
    company: 'Sample Company Ltd'
  },
  {
    name: 'BT-2024-00002',
    date: '2024-01-16',
    description: 'CHECK PAYMENT TO VENDOR XYZ',
    reference_number: 'CHK789',
    deposit: 0,
    withdrawal: 2500.00,
    currency: 'USD',
    allocated_amount: 0,
    unallocated_amount: 2500.00,
    party_type: 'Supplier',
    party: 'Vendor XYZ Ltd',
    bank_account: 'HDFC Bank - 12345',
    company: 'Sample Company Ltd'
  },
  {
    name: 'BT-2024-00003',
    date: '2024-01-17',
    description: 'SALARY PAYMENT BATCH',
    reference_number: 'SAL-JAN-2024',
    deposit: 0,
    withdrawal: 45000.00,
    currency: 'USD',
    allocated_amount: 0,
    unallocated_amount: 45000.00,
    party_type: null,
    party: null,
    bank_account: 'HDFC Bank - 12345',
    company: 'Sample Company Ltd'
  },
  {
    name: 'BT-2024-00004',
    date: '2024-01-18',
    description: 'CUSTOMER PAYMENT - INVOICE #INV-001',
    reference_number: 'INV-001',
    deposit: 8750.00,
    withdrawal: 0,
    currency: 'USD',
    allocated_amount: 0,
    unallocated_amount: 8750.00,
    party_type: 'Customer',
    party: 'ABC Customer Inc',
    bank_account: 'HDFC Bank - 12345',
    company: 'Sample Company Ltd'
  },
  {
    name: 'BT-2024-00005',
    date: '2024-01-19',
    description: 'BANK CHARGES - MONTHLY FEE',
    reference_number: 'BCH-JAN-2024',
    deposit: 0,
    withdrawal: 25.00,
    currency: 'USD',
    allocated_amount: 0,
    unallocated_amount: 25.00,
    party_type: null,
    party: null,
    bank_account: 'HDFC Bank - 12345',
    company: 'Sample Company Ltd'
  }
])

// Event handlers
const handleReconcileClick = (transaction) => {
  console.log('Reconcile clicked for transaction:', transaction)
  
  selectedTransaction.value = transaction
  showReconciliationDialog.value = true
  
  // Clear any previous status messages
  statusMessage.value = ''
}

const handleSelectionChange = (selectedTransactions) => {
  console.log('Selection changed:', selectedTransactions)
  // Handle bulk selection if needed
}

const handleReconciliationComplete = (result) => {
  console.log('Reconciliation completed:', result)
  
  // Show success message
  statusMessage.value = `Transaction ${result.transaction_name} reconciled successfully!`
  statusMessageClass.value = 'bg-green-50 text-green-800 border border-green-200'
  
  // Close dialog
  showReconciliationDialog.value = false
  
  // In a real application, you would refresh the transaction data here
  // For this demo, we'll just simulate removing the reconciled transaction
  setTimeout(() => {
    const index = sampleTransactions.value.findIndex(t => t.name === result.transaction_name)
    if (index > -1) {
      sampleTransactions.value.splice(index, 1)
    }
  }, 1000)
  
  // Clear status message after a few seconds
  setTimeout(() => {
    statusMessage.value = ''
  }, 5000)
}

const handleReconciliationError = (error) => {
  console.error('Reconciliation error:', error)
  
  // Show error message
  statusMessage.value = `Error reconciling transaction: ${error.message || 'Unknown error'}`
  statusMessageClass.value = 'bg-red-50 text-red-800 border border-red-200'
  
  // Clear error message after a few seconds
  setTimeout(() => {
    statusMessage.value = ''
  }, 7000)
}
</script>

<style scoped>
.bank-reconciliation-example {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Ensure proper spacing and responsive design */
@media (max-width: 768px) {
  .bank-reconciliation-example {
    padding: 1rem;
  }
}
</style> 