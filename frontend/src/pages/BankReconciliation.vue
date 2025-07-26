<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <div class="bg-white shadow-sm border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-4">
          <div>
            <h1 class="text-2xl font-semibold text-gray-900">
              Bank Reconciliation
            </h1>
            <p class="text-sm text-gray-600">
              Reconcile bank transactions with accounting entries
            </p>
          </div>
          <div class="flex space-x-3">
            <Button
              variant="outline"
              @click="uploadStatement"
              :loading="uploading"
            >
              Upload Statement
            </Button>
            <Button
              variant="outline"
              @click="autoReconcile"
              :loading="autoReconciling"
            >
              Auto Reconcile
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Filters Panel -->
      <FiltersPanel
        @filter-change="handleFilterChange"
      />

      <!-- Number Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <NumberCard
          title="Opening Balance"
          :value="summary.openingBalance"
          :currency="summary.currency"
          variant="info"
        />
        <NumberCard
          title="Cleared Balance"
          :value="summary.clearedBalance"
          :currency="summary.currency"
          variant="success"
        />
        <NumberCard
          title="Difference"
          :value="summary.difference"
          :currency="summary.currency"
          :variant="summary.difference === 0 ? 'success' : 'danger'"
        />
      </div>

      <!-- Transactions Table -->
      <div class="bg-white shadow rounded-lg">
        <div class="px-6 py-4 border-b border-gray-200">
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-medium text-gray-900">
              Unreconciled Transactions
            </h3>
            <div class="flex items-center space-x-4">
              <label class="flex items-center">
                <input
                  type="checkbox"
                  v-model="showReconciled"
                  class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span class="ml-2 text-sm text-gray-700">
                  Show Reconciled
                </span>
              </label>
              <Button
                variant="outline"
                size="sm"
                @click="getUnreconciledEntries"
                :loading="loading"
              >
                <FeatherIcon name="refresh-cw" class="w-4 h-4 mr-2" />
                Get Entries
              </Button>
            </div>
          </div>
        </div>
        
        <TransactionsTable
          :transactions="transactions"
          :loading="loading"
          @selection-change="handleSelectionChange"
          @reconcile="handleReconcile"
        />
      </div>
    </div>

    <!-- Reconciliation Dialog -->
    <ReconciliationDialog
      v-model="showReconciliationDialog"
      :bank-transaction="selectedTransaction"
      :selected-vouchers="selectedVouchers"
      @reconciled="handleReconciled"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Button } from 'frappe-ui'
import FiltersPanel from '../components/FiltersPanel.vue'
import NumberCard from '@/components/NumberCard.vue'
import TransactionsTable from '@/components/TransactionsTable.vue'
import ReconciliationDialog from '@/components/ReconciliationDialog.vue'
import { useBankReconciliation } from '../composables/useBankReconciliation'

// Component setup
const {
  transactions,
  summary,
  loading,
  uploading,
  autoReconciling,
  getUnreconciledEntries,
  uploadStatement,
  autoReconcile,
  reconcileTransaction
} = useBankReconciliation()

const showReconciled = ref(false)
const showReconciliationDialog = ref(false)
const selectedTransaction = ref(null)
const selectedVouchers = ref([])

// Event handlers
const handleFilterChange = (filters) => {
  console.log('handleFilterChange', filters)
  getUnreconciledEntries({
    company: filters.company,
    bank_account: filters.bankAccount,
    from_date: filters.fromDate,
    to_date: filters.toDate
  })
}

const handleSelectionChange = (selection) => {
  selectedVouchers.value = selection
}

const handleReconcile = (transaction) => {
  selectedTransaction.value = transaction
  showReconciliationDialog.value = true
}

const handleReconciled = () => {
  showReconciliationDialog.value = false
  selectedTransaction.value = null
  handleFilterChange({})
}
</script> 