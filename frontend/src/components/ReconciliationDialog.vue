<template>
  <Dialog 
    v-model="show" 
    :options="{
      title: 'Reconcile the Bank Transaction',
      size: '7xl'
    }"
  >
    <template #body-content>
      <div class="space-y-6">
        <!-- Action Selection Section -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Action</label>
            <FormControl
              type="select"
              v-model="actionMode"
              :options="actionOptions"
              @change="onActionModeChange"
            />
          </div>
          <div v-if="actionMode === 'Create Voucher'">
            <label class="block text-sm font-medium text-gray-700 mb-2">Document Type</label>
            <FormControl
              type="select"
              v-model="documentType"
              :options="documentTypeOptions"
            />
          </div>
        </div>

        <!-- Match Against Voucher Section -->
        <div v-if="actionMode === 'Match Against Voucher'" class="space-y-4">
          <!-- Filters Section -->
          <div class="border rounded-lg p-4 bg-gray-50">
            <h3 class="text-sm font-medium text-gray-900 mb-3">Filters</h3>
            
            <!-- Document Type Checkboxes -->
            <div class="grid grid-cols-3 gap-4 mb-4">
              <div v-for="docType in availableDocTypes" :key="docType.value">
                <label class="flex items-center">
                  <input
                    type="checkbox"
                    v-model="selectedDocTypes"
                    :value="docType.value"
                    @change="onFilterChange"
                    class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  />
                  <span class="ml-2 text-sm text-gray-700">{{ docType.label }}</span>
                </label>
              </div>
            </div>

            <!-- Additional Filters -->
            <div class="grid grid-cols-3 gap-4">
              <div>
                <label class="flex items-center">
                  <input
                    type="checkbox"
                    v-model="exactMatch"
                    @change="onFilterChange"
                    class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  />
                  <span class="ml-2 text-sm text-gray-700">Show Only Exact Amount</span>
                </label>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">From Date</label>
                <FormControl
                  type="date"
                  v-model="fromDate"
                  @change="onFilterChange"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">To Date</label>
                <FormControl
                  type="date"
                  v-model="toDate"
                  @change="onFilterChange"
                />
              </div>
            </div>
          </div>

          <!-- Selected Vouchers Summary -->
          <div v-if="selectedVouchers.length > 0" class="border rounded-lg p-4 bg-blue-50">
            <div class="text-center">
              <h5 class="font-bold text-blue-900">
                Total ({{ selectedVouchers.length }} selected): {{ formatCurrency(voucherTotal, transaction?.currency) }}
              </h5>
            </div>
          </div>

          <!-- Voucher Selection Table -->
          <div v-if="showVoucherTable" class="border rounded-lg">
            <div class="p-3 bg-gray-50 border-b">
              <h4 class="text-sm font-medium text-gray-900">
                Available Vouchers ({{ availableVouchers.length }} found)
              </h4>
            </div>
            <div class="max-h-96 overflow-y-auto">
              <VoucherSelectionTable
                :vouchers="availableVouchers"
                :loading="loadingVouchers"
                v-model:selected="selectedVouchers"
                @selection-change="onVoucherSelectionChange"
              />
            </div>
          </div>

          <!-- No Matching Vouchers Message -->
          <div v-else-if="!loadingVouchers && searchAttempted" class="text-center py-8">
            <div class="text-gray-500">No Matching Vouchers Found</div>
          </div>
        </div>

        <!-- Create Voucher Section -->
        <div v-if="actionMode === 'Create Voucher'" class="space-y-4">
          <div class="border rounded-lg p-4">
            <h3 class="text-sm font-medium text-gray-900 mb-3">Voucher Details</h3>
            <!-- Voucher creation form fields will go here -->
            <div class="text-gray-500">Voucher creation form coming soon...</div>
          </div>
        </div>

        <!-- Update Bank Transaction Section -->
        <div v-if="actionMode === 'Update Bank Transaction'" class="space-y-4">
          <div class="border rounded-lg p-4">
            <h3 class="text-sm font-medium text-gray-900 mb-3">Update Transaction</h3>
            <!-- Transaction update form fields will go here -->
            <div class="text-gray-500">Transaction update form coming soon...</div>
          </div>
        </div>

        <!-- Bank Transaction Details (Read-only) -->
        <div class="border rounded-lg p-4 bg-gray-50">
          <h3 class="text-sm font-medium text-gray-900 mb-3">Transaction Details</h3>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <label class="font-medium text-gray-700">Date:</label>
              <span class="ml-2 text-gray-900">{{ formatDate(transaction?.date) }}</span>
            </div>
            <div>
              <label class="font-medium text-gray-700">Amount:</label>
              <span class="ml-2 text-gray-900" :class="amountClass">
                {{ formatCurrency(transactionAmount, transaction?.currency) }}
              </span>
            </div>
            <div class="col-span-2">
              <label class="font-medium text-gray-700">Description:</label>
              <span class="ml-2 text-gray-900">{{ transaction?.description }}</span>
            </div>
            <div>
              <label class="font-medium text-gray-700">Allocated:</label>
              <span class="ml-2 text-gray-900">{{ formatCurrency(allocatedAmount, transaction?.currency) }}</span>
            </div>
            <div>
              <label class="font-medium text-gray-700">Unallocated:</label>
              <span class="ml-2 text-gray-900">{{ formatCurrency(unallocatedAmount, transaction?.currency) }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template #actions>
      <div class="flex gap-2">
        <Button variant="ghost" @click="handleCancel">Cancel</Button>
        <Button 
          variant="solid" 
          :loading="processing"
          @click="handleReconcile"
          :disabled="!canReconcile"
        >
          {{ actionMode === 'Match Against Voucher' ? 'Reconcile' : actionMode === 'Create Voucher' ? 'Create & Reconcile' : 'Update' }}
        </Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Dialog, Button, FormControl } from 'frappe-ui'
import { formatDate, formatCurrency } from '../utils/formatters'
import VoucherSelectionTable from './VoucherSelectionTable.vue'
import { useReconciliation } from '../composables/useReconciliation'

// Props
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  transaction: {
    type: Object,
    default: null
  },
  company: {
    type: String,
    default: ''
  },
  bankAccount: {
    type: String,
    default: ''
  }
})

// Emits
const emit = defineEmits(['update:modelValue', 'reconciled', 'error'])

// Composables
const { 
  searchVouchers, 
  reconcileVouchers, 
  createPaymentEntriesForInvoices,
  isLoading: processing 
} = useReconciliation()

// Dialog visibility
const show = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// Form state
const actionMode = ref('Match Against Voucher')
const documentType = ref('Payment Entry')
const selectedDocTypes = ref(['payment_entry', 'journal_entry'])
const exactMatch = ref(false)
const fromDate = ref('')
const toDate = ref('')

// Voucher data
const availableVouchers = ref([])
const selectedVouchers = ref([])
const loadingVouchers = ref(false)
const searchAttempted = ref(false)

// Action and document type options
const actionOptions = [
  { label: 'Match Against Voucher', value: 'Match Against Voucher' },
  { label: 'Create Voucher', value: 'Create Voucher' },
  { label: 'Update Bank Transaction', value: 'Update Bank Transaction' }
]

const documentTypeOptions = [
  { label: 'Payment Entry', value: 'Payment Entry' },
  { label: 'Journal Entry', value: 'Journal Entry' }
]

const availableDocTypes = [
  { label: 'Payment Entry', value: 'payment_entry' },
  { label: 'Journal Entry', value: 'journal_entry' },
  { label: 'Unpaid Sales Invoice', value: 'unpaid_sales_invoice' },
  { label: 'Unpaid Purchase Invoice', value: 'unpaid_purchase_invoice' }
]

// Computed properties
const transactionAmount = computed(() => {
  if (!props.transaction) return 0
  return (props.transaction.deposit || 0) - (props.transaction.withdrawal || 0)
})

const amountClass = computed(() => {
  return transactionAmount.value > 0 ? 'text-green-600' : 'text-red-600'
})

const allocatedAmount = computed(() => {
  return props.transaction?.allocated_amount || 0
})

const unallocatedAmount = computed(() => {
  if (!props.transaction) return 0
  return (props.transaction.unallocated_amount || transactionAmount.value) - voucherTotal.value
})

const voucherTotal = computed(() => {
  return selectedVouchers.value.reduce((total, voucher) => {
    return total + (voucher.amount || 0)
  }, 0)
})

const showVoucherTable = computed(() => {
  return availableVouchers.value.length > 0 && !loadingVouchers.value
})

const canReconcile = computed(() => {
  if (actionMode.value === 'Match Against Voucher') {
    return selectedVouchers.value.length > 0
  }
  return true // For other modes, we'll validate based on form completion
})

watch(props.transaction, () => {
  console.log('Transaction changed:', props.transaction)
})

// Methods
const onActionModeChange = () => {
  // Reset state when action mode changes
  selectedVouchers.value = []
  availableVouchers.value = []
  searchAttempted.value = false
}

const onFilterChange = async () => {
  if (actionMode.value === 'Match Against Voucher') {
    await searchForVouchers()
  }
}

const onVoucherSelectionChange = (selection) => {
  selectedVouchers.value = selection
  console.log('Selected vouchers:', selectedVouchers.value)
}

const searchForVouchers = async () => {
  if (!props.transaction) {
    return
  }

  // Clear vouchers if no document types are selected
  if (selectedDocTypes.value.length === 0) {
    availableVouchers.value = []
    selectedVouchers.value = []
    searchAttempted.value = true
    return
  }

  loadingVouchers.value = true
  searchAttempted.value = true
  
  try {
    const result = await searchVouchers({
      bankTransactionName: props.transaction.name,
      documentTypes: selectedDocTypes.value,
      fromDate: fromDate.value,
      toDate: toDate.value,
      exactMatch: exactMatch.value,
      filterByReferenceDate: false
    })
    
    availableVouchers.value = result || []
    // Clear any previously selected vouchers when search results change
    selectedVouchers.value = []
    console.log('Found vouchers:', availableVouchers.value.length)
  } catch (error) {
    console.error('Error searching vouchers:', error)
    emit('error', error)
  } finally {
    loadingVouchers.value = false
  }
}

const handleReconcile = async () => {
  try {
    if (actionMode.value === 'Match Against Voucher') {
      await processVoucherMatching()
    } else if (actionMode.value === 'Create Voucher') {
      // TODO: Implement voucher creation
      console.log('Create voucher not implemented yet')
    } else if (actionMode.value === 'Update Bank Transaction') {
      // TODO: Implement transaction update
      console.log('Update transaction not implemented yet')
    }
  } catch (error) {
    console.error('Reconciliation error:', error)
    emit('error', error)
  }
}

const processVoucherMatching = async () => {
  if (selectedVouchers.value.length === 0) {
    return
  }

  // Separate unpaid invoices from regular vouchers
  const unpaidInvoices = selectedVouchers.value.filter(v => 
    v.doctype === 'Unpaid Sales Invoice' || v.doctype === 'Unpaid Purchase Invoice'
  )
  const regularVouchers = selectedVouchers.value.filter(v => 
    v.doctype !== 'Unpaid Sales Invoice' && v.doctype !== 'Unpaid Purchase Invoice'
  )

  console.log('Processing reconciliation:', {
    unpaidInvoices: unpaidInvoices.length,
    regularVouchers: regularVouchers.length
  })

  // Process unpaid invoices first if any
  if (unpaidInvoices.length > 0) {
    const invoiceData = unpaidInvoices.map(invoice => ({
      doctype: invoice.doctype,
      name: invoice.name,
      allocated_amount: invoice.amount
    }))

    await createPaymentEntriesForInvoices(
      props.transaction.name,
      invoiceData,
      regularVouchers.length === 0 // auto-reconcile if no regular vouchers
    )
  }

  // Process regular vouchers if any
  if (regularVouchers.length > 0) {
    const voucherData = regularVouchers.map(voucher => ({
      payment_doctype: voucher.doctype,
      payment_name: voucher.name,
      amount: voucher.amount
    }))

    await reconcileVouchers(props.transaction.name, voucherData)
  }

  // Emit success
  emit('reconciled', { 
    transaction_name: props.transaction.name,
    vouchers_processed: selectedVouchers.value.length
  })
}

const handleCancel = () => {
  show.value = false
}

const initializeDialog = () => {
  if (props.transaction) {
    // Set default date range based on transaction date
    const transactionDate = new Date(props.transaction.date)
    const fromDateObj = new Date(transactionDate)
    fromDateObj.setDate(fromDateObj.getDate() - 30) // 30 days before
    const toDateObj = new Date(transactionDate)
    toDateObj.setDate(toDateObj.getDate() + 30) // 30 days after

    fromDate.value = fromDateObj.toISOString().split('T')[0]
    toDate.value = toDateObj.toISOString().split('T')[0]

    // Reset state
    selectedVouchers.value = []
    availableVouchers.value = []
    searchAttempted.value = false
    
    // Initial search for vouchers
    setTimeout(() => {
      if (actionMode.value === 'Match Against Voucher') {
        searchForVouchers()
      }
    }, 300)
  }
}

// Watchers
watch(() => props.transaction, () => {
  if (props.transaction && show.value) {
    initializeDialog()
  }
}, { immediate: true })

watch(show, (newValue) => {
  if (newValue && props.transaction) {
    initializeDialog()
  }
})
</script> 