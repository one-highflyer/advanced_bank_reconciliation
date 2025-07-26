<template>
  <div class="overflow-x-auto">
    <ListView
      :columns="columns"
      :data="vouchers"
      :selectable="true"
      :selected="selected"
      @selection-change="$emit('selection-change', $event)"
    >
      <template #cell-date="{ row }">
        <span class="text-sm text-gray-900">
          {{ formatDate(row.posting_date || row.date) }}
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

      <template #cell-party="{ row }">
        <span class="text-sm text-gray-900">
          {{ row.party || row.party_name || '-' }}
        </span>
      </template>

      <template #cell-reference="{ row }">
        <span class="text-sm text-gray-900">
          {{ row.reference_no || row.name || '-' }}
        </span>
      </template>

      <template #cell-status="{ row }">
        <span 
          class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
          :class="statusClasses(row.status || row.docstatus)"
        >
          {{ getStatusText(row.status || row.docstatus) }}
        </span>
      </template>

      <template #cell-actions="{ row }">
        <div class="flex items-center space-x-2">
          <Button
            size="sm"
            variant="outline"
            @click="viewVoucher(row)"
          >
            <FeatherIcon name="eye" class="w-4 h-4 mr-1" />
            View
          </Button>
        </div>
      </template>
    </ListView>

    <!-- Empty State -->
    <div 
      v-if="vouchers.length === 0"
      class="text-center py-8"
    >
      <FeatherIcon 
        name="search" 
        class="mx-auto h-8 w-8 text-gray-400"
      />
      <h3 class="mt-2 text-sm font-medium text-gray-900">
        No vouchers found
      </h3>
      <p class="mt-1 text-sm text-gray-500">
        Try adjusting your search criteria.
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatDate, formatCurrency } from '@/utils/formatters'

// Props
const props = defineProps({
  vouchers: {
    type: Array,
    default: () => []
  },
  selected: {
    type: Array,
    default: () => []
  }
})

// Emits
const emit = defineEmits(['selection-change'])

// Table columns configuration
const columns = computed(() => [
  {
    key: 'date',
    label: 'Date',
    sortable: true
  },
  {
    key: 'reference',
    label: 'Reference',
    sortable: true
  },
  {
    key: 'party',
    label: 'Party',
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
    0: 'bg-yellow-100 text-yellow-800', // Draft
    1: 'bg-green-100 text-green-800',   // Submitted
    2: 'bg-red-100 text-red-800',       // Cancelled
    'Draft': 'bg-yellow-100 text-yellow-800',
    'Submitted': 'bg-green-100 text-green-800',
    'Cancelled': 'bg-red-100 text-red-800',
    'Paid': 'bg-blue-100 text-blue-800',
    'Unpaid': 'bg-orange-100 text-orange-800'
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

const getStatusText = (status) => {
  const statusMap = {
    0: 'Draft',
    1: 'Submitted',
    2: 'Cancelled',
    'Draft': 'Draft',
    'Submitted': 'Submitted',
    'Cancelled': 'Cancelled',
    'Paid': 'Paid',
    'Unpaid': 'Unpaid'
  }
  return statusMap[status] || status
}

const viewVoucher = (voucher) => {
  // Open voucher in new tab or modal
  if (voucher.doctype && voucher.name) {
    window.open(`/app/${voucher.doctype}/${voucher.name}`, '_blank')
  }
}
</script> 