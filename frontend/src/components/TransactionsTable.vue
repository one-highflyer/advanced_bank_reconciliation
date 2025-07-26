<template>
  <div class="overflow-x-auto">
    <ListView
      :columns="columns"
      :data="transactions"
      :loading="loading"
      :selectable="true"
      @selection-change="$emit('selection-change', $event)"
    >
      <template #cell-date="{ row }">
        <span class="text-sm text-gray-900">
          {{ formatDate(row.date) }}
        </span>
      </template>

      <template #cell-amount="{ row }">
        <span 
          class="text-sm font-medium"
          :class="row.amount > 0 ? 'text-green-600' : 'text-red-600'"
        >
          {{ formatCurrency(row.amount, row.currency) }}
        </span>
      </template>

      <template #cell-status="{ row }">
        <span 
          class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
          :class="statusClasses(row.status)"
        >
          {{ row.status }}
        </span>
      </template>

      <template #cell-actions="{ row }">
        <div class="flex items-center space-x-2">
          <Button
            size="sm"
            variant="outline"
            @click="$emit('reconcile', row)"
          >
            <FeatherIcon name="link" class="w-4 h-4 mr-1" />
            Reconcile
          </Button>
          
          <Button
            size="sm"
            variant="outline"
            @click="showTransactionDetails(row)"
          >
            <FeatherIcon name="eye" class="w-4 h-4 mr-1" />
            View
          </Button>
        </div>
      </template>
    </ListView>

    <!-- Empty State -->
    <div 
      v-if="!loading && transactions.length === 0"
      class="text-center py-12"
    >
      <FeatherIcon 
        name="inbox" 
        class="mx-auto h-12 w-12 text-gray-400"
      />
      <h3 class="mt-2 text-sm font-medium text-gray-900">
        No transactions found
      </h3>
      <p class="mt-1 text-sm text-gray-500">
        Try adjusting your filters or upload a bank statement.
      </p>
    </div>

    <!-- Transaction Details Dialog -->
    <Dialog
      v-model="showDetailsDialog"
      title="Transaction Details"
      size="lg"
    >
      <div v-if="selectedTransaction" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700">
              Date
            </label>
            <p class="mt-1 text-sm text-gray-900">
              {{ formatDate(selectedTransaction.date) }}
            </p>
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700">
              Amount
            </label>
            <p class="mt-1 text-sm text-gray-900">
              {{ formatCurrency(selectedTransaction.amount, selectedTransaction.currency) }}
            </p>
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700">
              Description
            </label>
            <p class="mt-1 text-sm text-gray-900">
              {{ selectedTransaction.description }}
            </p>
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700">
              Reference
            </label>
            <p class="mt-1 text-sm text-gray-900">
              {{ selectedTransaction.reference || '-' }}
            </p>
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700">
              Status
            </label>
            <p class="mt-1">
              <span 
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                :class="statusClasses(selectedTransaction.status)"
              >
                {{ selectedTransaction.status }}
              </span>
            </p>
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700">
              Bank Account
            </label>
            <p class="mt-1 text-sm text-gray-900">
              {{ selectedTransaction.bank_account }}
            </p>
          </div>
        </div>
      </div>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { formatDate, formatCurrency } from '@/utils/formatters'

// Props
const props = defineProps({
  transactions: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['selection-change', 'reconcile'])

// Local state
const showDetailsDialog = ref(false)
const selectedTransaction = ref(null)

// Table columns configuration
const columns = computed(() => [
  {
    key: 'date',
    label: 'Date',
    sortable: true
  },
  {
    key: 'description',
    label: 'Description',
    sortable: true
  },
  {
    key: 'reference',
    label: 'Reference',
    sortable: true
  },
  {
    key: 'amount',
    label: 'Amount',
    sortable: true,
    align: 'right'
  },
  {
    key: 'status',
    label: 'Status',
    sortable: true
  },
  {
    key: 'actions',
    label: 'Actions',
    sortable: false,
    align: 'center'
  }
])

// Methods
const statusClasses = (status) => {
  const classes = {
    'Unreconciled': 'bg-yellow-100 text-yellow-800',
    'Reconciled': 'bg-green-100 text-green-800',
    'Validated': 'bg-blue-100 text-blue-800',
    'Error': 'bg-red-100 text-red-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

const showTransactionDetails = (transaction) => {
  selectedTransaction.value = transaction
  showDetailsDialog.value = true
}
</script> 