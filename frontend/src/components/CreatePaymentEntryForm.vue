<template>
  <div class="space-y-6">
    <div class="bg-blue-50 rounded-lg p-4">
      <h4 class="text-sm font-medium text-blue-900 mb-2">
        Create Payment Entry
      </h4>
      <p class="text-sm text-blue-700">
        Create a new payment entry based on the bank transaction details.
      </p>
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Payment Type -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Payment Type
        </label>
        <Select
          v-model="form.payment_type"
          :options="paymentTypeOptions"
          placeholder="Select Payment Type"
          required
        />
      </div>

      <!-- Party Type -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Party Type
        </label>
        <Select
          v-model="form.party_type"
          :options="partyTypeOptions"
          placeholder="Select Party Type"
          required
        />
      </div>

      <!-- Party -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Party
        </label>
        <Select
          v-model="form.party"
          :options="partyOptions"
          placeholder="Select Party"
          :disabled="!form.party_type"
          required
        />
      </div>

      <!-- Payment Date -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Payment Date
        </label>
        <input
          type="date"
          v-model="form.payment_date"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          required
        />
      </div>

      <!-- Amount -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Amount
        </label>
        <input
          type="number"
          v-model="form.amount"
          step="0.01"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          required
        />
      </div>

      <!-- Reference -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Reference
        </label>
        <input
          type="text"
          v-model="form.reference_no"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          :placeholder="bankTransaction?.reference || ''"
        />
      </div>

      <!-- Remarks -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Remarks
        </label>
        <textarea
          v-model="form.remarks"
          rows="3"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          :placeholder="bankTransaction?.description || ''"
        ></textarea>
      </div>

      <!-- Submit Button -->
      <div class="flex justify-end space-x-3 pt-4">
        <Button
          type="button"
          variant="outline"
          @click="$emit('cancel')"
        >
          Cancel
        </Button>
        
        <Button
          type="submit"
          :loading="creating"
        >
          Create Payment Entry
        </Button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useReconciliation } from '@/composables/useReconciliation'

// Props
const props = defineProps({
  bankTransaction: {
    type: Object,
    required: true
  }
})

// Emits
const emit = defineEmits(['created', 'cancel'])

// Composables
const { createPaymentEntry, creatingPayment } = useReconciliation()

// Form data
const form = ref({
  payment_type: '',
  party_type: '',
  party: '',
  payment_date: '',
  amount: 0,
  reference_no: '',
  remarks: ''
})

// Options
const paymentTypeOptions = [
  { label: 'Pay', value: 'Pay' },
  { label: 'Receive', value: 'Receive' },
  { label: 'Internal Transfer', value: 'Internal Transfer' }
]

const partyTypeOptions = [
  { label: 'Customer', value: 'Customer' },
  { label: 'Supplier', value: 'Supplier' },
  { label: 'Employee', value: 'Employee' },
  { label: 'Shareholder', value: 'Shareholder' },
  { label: 'Member', value: 'Member' },
  { label: 'Student', value: 'Student' }
]

const partyOptions = ref([])

// Computed
const creating = computed(() => creatingPayment.value)

// Methods
const loadParties = async (partyType) => {
  if (!partyType) {
    partyOptions.value = []
    return
  }
  
  try {
    const result = await frappe.call({
      method: 'frappe.client.get_list',
      args: {
        doctype: partyType,
        fields: ['name', 'customer_name', 'supplier_name', 'employee_name'],
        order_by: 'name'
      }
    })
    
    partyOptions.value = result.message.map(party => ({
      label: party.customer_name || party.supplier_name || party.employee_name || party.name,
      value: party.name
    }))
  } catch (error) {
    console.error('Error loading parties:', error)
    partyOptions.value = []
  }
}

const handleSubmit = async () => {
  try {
    const paymentData = {
      ...form.value,
      bank_account: props.bankTransaction.bank_account,
      company: props.bankTransaction.company
    }
    
    const result = await createPaymentEntry(paymentData)
    emit('created', result)
  } catch (error) {
    console.error('Error creating payment entry:', error)
  }
}

const initializeForm = () => {
  if (props.bankTransaction) {
    form.value.payment_date = props.bankTransaction.date
    form.value.amount = Math.abs(props.bankTransaction.amount)
    form.value.reference_no = props.bankTransaction.reference || ''
    form.value.remarks = props.bankTransaction.description || ''
    
    // Determine payment type based on amount
    form.value.payment_type = props.bankTransaction.amount > 0 ? 'Receive' : 'Pay'
  }
}

// Watchers
watch(() => form.value.party_type, (newPartyType) => {
  form.value.party = ''
  loadParties(newPartyType)
})

// Lifecycle
onMounted(() => {
  initializeForm()
})
</script> 