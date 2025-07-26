<template>
  <Dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="Reconcile Transaction"
    size="xl"
    @close="handleClose"
  >
    <div v-if="bankTransaction" class="space-y-6">
      <!-- Transaction Summary -->
      <div class="bg-gray-50 rounded-lg p-4">
        <h4 class="text-sm font-medium text-gray-900 mb-3">
          Bank Transaction Details
        </h4>
        <div class="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span class="text-gray-500">Date:</span>
            <span class="ml-2 font-medium">{{ formatDate(bankTransaction.date) }}</span>
          </div>
          <div>
            <span class="text-gray-500">Amount:</span>
            <span class="ml-2 font-medium">{{ formatCurrency(bankTransaction.amount, bankTransaction.currency) }}</span>
          </div>
          <div>
            <span class="text-gray-500">Description:</span>
            <span class="ml-2 font-medium">{{ bankTransaction.description }}</span>
          </div>
        </div>
      </div>

      <!-- Reconciliation Type Selection -->
      <div>
        <h4 class="text-sm font-medium text-gray-900 mb-3">
          Reconciliation Type
        </h4>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <button
            v-for="type in reconciliationTypes"
            :key="type.value"
            @click="selectedType = type.value"
            class="p-4 border rounded-lg text-left transition-colors"
            :class="selectedType === type.value ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'"
          >
            <div class="flex items-center">
              <FeatherIcon :name="type.icon" class="w-5 h-5 mr-3" />
              <div>
                <div class="font-medium text-gray-900">{{ type.label }}</div>
                <div class="text-sm text-gray-500">{{ type.description }}</div>
              </div>
            </div>
          </button>
        </div>
      </div>

      <!-- Voucher Selection -->
      <div v-if="selectedType === 'match'">
        <div class="flex justify-between items-center mb-3">
          <h4 class="text-sm font-medium text-gray-900">
            Select Vouchers to Reconcile
          </h4>
          <Button
            size="sm"
            variant="outline"
            @click="searchVouchers"
            :loading="searchingVouchers"
          >
            <FeatherIcon name="search" class="w-4 h-4 mr-1" />
            Search Vouchers
          </Button>
        </div>

        <!-- Voucher Categories -->
        <div class="space-y-4">
          <!-- Payment Entries -->
          <div v-if="vouchers.payments.length > 0">
            <h5 class="text-sm font-medium text-gray-700 mb-2">
              Payment Entries
            </h5>
            <VoucherSelectionTable
              :vouchers="vouchers.payments"
              :selected="selectedVouchers"
              @selection-change="handleVoucherSelection"
            />
          </div>

          <!-- Journal Entries -->
          <div v-if="vouchers.journals.length > 0">
            <h5 class="text-sm font-medium text-gray-700 mb-2">
              Journal Entries
            </h5>
            <VoucherSelectionTable
              :vouchers="vouchers.journals"
              :selected="selectedVouchers"
              @selection-change="handleVoucherSelection"
            />
          </div>

          <!-- Unpaid Invoices -->
          <div v-if="vouchers.invoices.length > 0">
            <h5 class="text-sm font-medium text-gray-700 mb-2">
              Unpaid Invoices
            </h5>
            <VoucherSelectionTable
              :vouchers="vouchers.invoices"
              :selected="selectedVouchers"
              @selection-change="handleVoucherSelection"
            />
          </div>
        </div>

        <!-- Allocation Summary -->
        <div v-if="selectedVouchers.length > 0" class="bg-blue-50 rounded-lg p-4 mt-4">
          <h5 class="text-sm font-medium text-gray-900 mb-2">
            Allocation Summary
          </h5>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span class="text-gray-500">Total Selected:</span>
              <span class="ml-2 font-medium">{{ formatCurrency(totalSelected, bankTransaction.currency) }}</span>
            </div>
            <div>
              <span class="text-gray-500">Remaining:</span>
              <span class="ml-2 font-medium" :class="remainingAmount === 0 ? 'text-green-600' : 'text-red-600'">
                {{ formatCurrency(remainingAmount, bankTransaction.currency) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Create Payment Entry Form -->
      <div v-if="selectedType === 'create_payment'">
        <CreatePaymentEntryForm
          :bank-transaction="bankTransaction"
          @created="handlePaymentCreated"
        />
      </div>

      <!-- Create Journal Entry Form -->
      <div v-if="selectedType === 'create_journal'">
        <CreateJournalEntryForm
          :bank-transaction="bankTransaction"
          @created="handleJournalCreated"
        />
      </div>
    </div>

    <!-- Dialog Footer -->
    <template #footer>
      <div class="flex justify-end space-x-3">
        <Button
          variant="outline"
          @click="handleClose"
        >
          Cancel
        </Button>
        
        <Button
          v-if="selectedType === 'match' && canReconcile"
          @click="handleReconcile"
          :loading="reconciling"
        >
          Reconcile
        </Button>
        
        <Button
          v-if="selectedType === 'update'"
          @click="handleUpdate"
          :loading="updating"
        >
          Update Transaction
        </Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { formatDate, formatCurrency } from '@/utils/formatters'
import VoucherSelectionTable from './VoucherSelectionTable.vue'
import CreatePaymentEntryForm from './CreatePaymentEntryForm.vue'
import CreateJournalEntryForm from './CreateJournalEntryForm.vue'
import { useReconciliation } from '@/composables/useReconciliation'

// Props
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  bankTransaction: {
    type: Object,
    default: null
  },
  selectedVouchers: {
    type: Array,
    default: () => []
  }
})

// Emits
const emit = defineEmits(['update:modelValue', 'reconciled'])

// Composables
const { 
  vouchers, 
  searchingVouchers, 
  reconciling, 
  updating,
  searchVouchers, 
  reconcileVouchers, 
  updateTransaction 
} = useReconciliation()

// Local state
const selectedType = ref('match')
const selectedVouchers = ref([])

// Reconciliation types
const reconciliationTypes = [
  {
    value: 'match',
    label: 'Match Against Voucher',
    description: 'Select existing vouchers to reconcile',
    icon: 'link'
  },
  {
    value: 'create_payment',
    label: 'Create Payment Entry',
    description: 'Create a new payment entry',
    icon: 'plus-circle'
  },
  {
    value: 'create_journal',
    label: 'Create Journal Entry',
    description: 'Create a new journal entry',
    icon: 'file-text'
  },
  {
    value: 'update',
    label: 'Update Transaction',
    description: 'Update transaction details',
    icon: 'edit'
  }
]

// Computed
const totalSelected = computed(() => {
  return selectedVouchers.value.reduce((sum, voucher) => sum + voucher.amount, 0)
})

const remainingAmount = computed(() => {
  if (!props.bankTransaction) return 0
  return Math.abs(props.bankTransaction.amount) - totalSelected.value
})

const canReconcile = computed(() => {
  return selectedVouchers.value.length > 0 && Math.abs(remainingAmount.value) < 0.01
})

// Methods
const handleClose = () => {
  emit('update:modelValue', false)
  selectedType.value = 'match'
  selectedVouchers.value = []
}

const handleVoucherSelection = (selection) => {
  selectedVouchers.value = selection
}

const handleReconcile = async () => {
  if (!props.bankTransaction || selectedVouchers.value.length === 0) return
  
  try {
    await reconcileVouchers(props.bankTransaction.name, selectedVouchers.value)
    emit('reconciled')
    handleClose()
  } catch (error) {
    console.error('Reconciliation failed:', error)
  }
}

const handleUpdate = async () => {
  if (!props.bankTransaction) return
  
  try {
    await updateTransaction(props.bankTransaction.name)
    emit('reconciled')
    handleClose()
  } catch (error) {
    console.error('Update failed:', error)
  }
}

const handlePaymentCreated = (payment) => {
  emit('reconciled')
  handleClose()
}

const handleJournalCreated = (journal) => {
  emit('reconciled')
  handleClose()
}

// Watch for dialog open to search vouchers
watch(() => props.modelValue, (newValue) => {
  if (newValue && props.bankTransaction && selectedType.value === 'match') {
    searchVouchers(props.bankTransaction)
  }
})

// Watch for type changes
watch(selectedType, (newType) => {
  if (newType === 'match' && props.bankTransaction) {
    searchVouchers(props.bankTransaction)
  }
})
</script> 