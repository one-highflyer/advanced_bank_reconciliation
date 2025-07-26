<template>
  <div class="voucher-selection-table">
    <div v-if="loading" class="text-center py-8">
      <div class="text-gray-500">Loading vouchers...</div>
    </div>
    
    <div v-else-if="vouchers.length === 0" class="text-center py-8">
      <div class="text-gray-500">No vouchers found</div>
    </div>
    
    <div v-else>
      <ListView 
        :columns="columns" 
        :rows="transformedVouchers" 
        :options="{ 
          selectable: true,
          showTooltip: false,
          emptyState: { title: 'No vouchers found', description: 'No matching vouchers for this transaction' }
        }"
        row-key="id"
        v-model="selectedRows"
        @selection-change="handleSelectionChange"
      >
        <template #cell="{ item, row, column }">
          <!-- Document Type column -->
          <template v-if="column.key === 'document_type'">
            <span class="text-sm font-medium" :class="getDocTypeClass(row.document_type)">
              {{ row.document_type }}
            </span>
          </template>

          <!-- Document Name column -->
          <template v-else-if="column.key === 'document_name'">
            <a 
              :href="getDocumentUrl(row.document_type, row.document_name)"
              target="_blank"
              class="text-sm text-blue-600 hover:text-blue-800 hover:underline"
            >
              {{ row.document_name }}
            </a>
          </template>

          <!-- Reference Date column -->
          <template v-else-if="column.key === 'reference_date'">
            <span class="text-sm text-gray-900">
              {{ formatDate(row.reference_date) }}
            </span>
          </template>

          <!-- Amount column -->
          <template v-else-if="column.key === 'amount'">
            <span class="text-sm font-medium text-right block" :class="getAmountClass(row.amount)">
              {{ formatCurrency(row.amount, row.currency) }}
            </span>
          </template>

          <!-- Reference Number column -->
          <template v-else-if="column.key === 'reference_number'">
            <span class="text-sm text-gray-900">
              {{ row.reference_number || '-' }}
            </span>
          </template>

          <!-- Party column -->
          <template v-else-if="column.key === 'party'">
            <span class="text-sm text-gray-900">
              {{ row.party || '-' }}
            </span>
          </template>

          <!-- Default fallback -->
          <template v-else>
            <span class="text-sm text-gray-900">
              {{ item }}
            </span>
          </template>
        </template>
      </ListView>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ListView } from 'frappe-ui'
import { formatDate, formatCurrency } from '../utils/formatters'

// Props
const props = defineProps({
  vouchers: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  selected: {
    type: Array,
    default: () => []
  }
})

// Emits
const emit = defineEmits(['update:selected', 'selection-change'])

// Local state
const selectedRows = ref([])

// Table columns configuration
const columns = computed(() => [
  {
    key: 'document_type',
    label: 'Document Type',
    width: '140px'
  },
  {
    key: 'document_name',
    label: 'Document Name',
    width: '250px'
  },
  {
    key: 'reference_date',
    label: 'Reference Date',
    width: '120px'
  },
  {
    key: 'amount',
    label: 'Amount',
    width: '120px',
    align: 'right'
  },
  {
    key: 'reference_number',
    label: 'Reference Number',
    width: '180px'
  },
  {
    key: 'party',
    label: 'Party',
    width: '180px'
  }
])

// Transform voucher data to match expected format
const transformedVouchers = computed(() => {
  return props.vouchers.map((voucher, index) => {
    // Handle different voucher data formats from the API
    // The API returns arrays in the format from dialog_manager.js
    let docType, docName, amount, referenceDate, referenceNumber, party, currency
    
    if (Array.isArray(voucher)) {
      // Format: [?, docType, docName, amount, ?, referenceDate, ?, ?, ?, currency]
      docType = voucher[1] || 'Unknown'
      docName = voucher[2] || 'Unknown'
      amount = voucher[3] || 0
      referenceDate = voucher[5] || voucher[8] || new Date() // fallback logic from dialog_manager.js
      referenceNumber = voucher[4] || ''
      party = voucher[6] || ''
      currency = voucher[9] || 'USD'
    } else {
      // Object format
      docType = voucher.document_type || voucher.doctype || 'Unknown'
      docName = voucher.document_name || voucher.name || 'Unknown'
      amount = voucher.amount || voucher.remaining_amount || 0
      referenceDate = voucher.reference_date || voucher.date || new Date()
      referenceNumber = voucher.reference_number || voucher.reference || ''
      party = voucher.party || ''
      currency = voucher.currency || 'USD'
    }

    return {
      id: `${docType}-${docName}-${index}`, // Unique identifier for row selection
      document_type: docType,
      document_name: docName,
      amount: amount,
      reference_date: referenceDate,
      reference_number: referenceNumber,
      party: party,
      currency: currency,
      original_data: voucher // Keep original for processing
    }
  })
})

// Methods
const getDocTypeClass = (docType) => {
  const classes = {
    'Payment Entry': 'text-blue-600',
    'Journal Entry': 'text-purple-600',
    'Unpaid Sales Invoice': 'text-orange-600',
    'Unpaid Purchase Invoice': 'text-red-600'
  }
  return classes[docType] || 'text-gray-600'
}

const getAmountClass = (amount) => {
  return amount > 0 ? 'text-green-600' : 'text-red-600'
}

const getDocumentUrl = (docType, docName) => {
  // Generate Frappe document URL
  const cleanDocType = docType.replace(/^Unpaid /, '') // Remove "Unpaid" prefix
  return `/app/${cleanDocType.toLowerCase().replace(/ /g, '-')}/${docName}`
}

const handleSelectionChange = (selection) => {
  console.log('ListView selection changed:', selection)
  
  // Convert ListView selection back to voucher objects
  const selectedVouchers = selection.map(selectedId => {
    const voucher = transformedVouchers.value.find(v => v.id === selectedId)
    return {
      doctype: voucher.document_type,
      name: voucher.document_name,
      amount: voucher.amount,
      reference_date: voucher.reference_date,
      reference_number: voucher.reference_number,
      party: voucher.party,
      currency: voucher.currency,
      original_data: voucher.original_data
    }
  })

  console.log('Selected vouchers:', selectedVouchers)
  
  // Emit to parent components
  emit('update:selected', selectedVouchers)
  emit('selection-change', selectedVouchers)
}

// Watch for external changes to selected prop
watch(() => props.selected, (newSelected) => {
  if (newSelected && newSelected.length > 0) {
    // Update internal selection based on external prop changes
    selectedRows.value = newSelected.map(voucher => {
      const transformed = transformedVouchers.value.find(v => 
        v.document_name === voucher.name && v.document_type === voucher.doctype
      )
      return transformed?.id
    }).filter(Boolean)
  } else {
    selectedRows.value = []
  }
}, { deep: true })

// Watch for voucher changes to reset selection
watch(() => props.vouchers, () => {
  selectedRows.value = []
}, { deep: true })
</script>

<style scoped>
/* Custom styling for different voucher types */
.voucher-selection-table :deep(.list-row) {
  transition: all 0.2s ease-in-out;
}

.voucher-selection-table :deep(.list-row:hover) {
  background-color: rgba(59, 130, 246, 0.05);
}

.voucher-selection-table :deep(.list-row.selected) {
  background-color: rgba(59, 130, 246, 0.1);
  border-left: 3px solid rgb(59, 130, 246);
}

/* Ensure table works well in scrollable containers */
.voucher-selection-table :deep(.list-view) {
  height: auto;
}
</style> 