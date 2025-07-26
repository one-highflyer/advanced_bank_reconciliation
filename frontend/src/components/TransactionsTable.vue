<template>
  <div class="overflow-x-auto py-4 px-2">
    <ListView :columns="columns" :rows="transformedTransactions" :options="{
      selectable: false,
    }" row-key="name" @selection-change="$emit('selection-change', $event)">
      <template #cell="{ item, row, column }">
        <!-- Date column -->
        <template v-if="column.key === 'date'">
          <span class="text-sm text-gray-900">
            {{ formatDate(row.date) }}
          </span>
        </template>

        <!-- Description column -->
        <template v-else-if="column.key === 'description'">
          <span class="text-sm text-gray-900">
            {{ row.description }}
          </span>
        </template>

        <!-- Reference column -->
        <template v-else-if="column.key === 'reference'">
          <span class="text-sm text-gray-900">
            {{ row.reference }}
          </span>
        </template>

        <!-- Amount column -->
        <template v-else-if="column.key === 'amount'">
          <span class="flex justify-end text-sm font-medium"
            :class="row.amount > 0 ? 'text-green-600' : 'text-red-600'">
            {{ formatCurrency(row.amount, row.currency) }}
          </span>
        </template>

        <!-- Actions column -->
        <template v-else-if="column.key === 'actions'">
          <div class="flex items-center justify-center">
            <Button size="sm" variant="solid" icon-right="play" @click="$emit('reconcile', row)">
              Reconcile
            </Button>
          </div>
        </template>

        <!-- Default fallback -->
        <template v-else>
          <span class="text-sm text-gray-900">
            {{ item }}
          </span>
        </template>
      </template>
    </ListView>

    <!-- Empty State -->
    <div v-if="!loading && transformedTransactions.length === 0" class="text-center py-12">
      <FeatherIcon name="inbox" class="mx-auto h-12 w-12 text-gray-400" />
      <h3 class="mt-2 text-sm font-medium text-gray-900">
        No transactions found
      </h3>
      <p class="mt-1 text-sm text-gray-500">
        Try adjusting your filters or upload a bank statement.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ListView, Button, Dialog, FeatherIcon } from 'frappe-ui'
import { formatDate, formatCurrency } from '../utils/formatters'

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
const selectedTransaction = ref(null)

// Watch for changes in transactions prop
watch(() => props.transactions, (newTransactions, oldTransactions) => {
  console.log('TransactionsTable: transactions changed')
  console.log('New transactions length:', newTransactions?.length)

  if (newTransactions?.length > 0) {
    console.log('First transaction sample:', newTransactions[0])
    console.log('First transaction keys:', Object.keys(newTransactions[0]))
  }
}, { deep: true, immediate: true })

// Transform transactions to match expected format
const transformedTransactions = computed(() => {
  if (!props.transactions || !Array.isArray(props.transactions)) {
    console.log('TransactionsTable: No transactions or not an array')
    return []
  }

  console.log('TransactionsTable: Transforming', props.transactions.length, 'transactions')

  return props.transactions.map(transaction => {
    // Calculate amount from deposit/withdrawal
    const amount = (transaction.deposit || 0) - (transaction.withdrawal || 0)

    return {
      ...transaction,
      amount: amount,
      reference: transaction.reference_number || transaction.reference || '-',
      status: 'Unreconciled' // Default status
    }
  })
})

// Table columns configuration
const columns = computed(() => [
  {
    key: 'date',
    label: 'Date'
  },
  {
    key: 'description',
    label: 'Description'
  },
  {
    key: 'reference',
    label: 'Reference'
  },
  {
    key: 'amount',
    label: 'Amount',
    align: 'right'
  },
  {
    key: 'actions',
    label: 'Actions',
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

</script>