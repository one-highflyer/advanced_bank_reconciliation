<template>
  <div class="space-y-6">
    <div class="bg-blue-50 rounded-lg p-4">
      <h4 class="text-sm font-medium text-blue-900 mb-2">
        Create Journal Entry
      </h4>
      <p class="text-sm text-blue-700">
        Create a new journal entry based on the bank transaction details.
      </p>
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Posting Date -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Posting Date
        </label>
        <input
          type="date"
          v-model="form.posting_date"
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

      <!-- User Remark -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          User Remark
        </label>
        <textarea
          v-model="form.user_remark"
          rows="3"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          :placeholder="bankTransaction?.description || ''"
        ></textarea>
      </div>

      <!-- Journal Entry Accounts -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Journal Entry Accounts
        </label>
        <div class="space-y-3">
          <div 
            v-for="(account, index) in form.accounts" 
            :key="index"
            class="grid grid-cols-3 gap-3 p-3 border border-gray-200 rounded-md"
          >
            <!-- Account -->
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">
                Account
              </label>
              <Select
                v-model="account.account"
                :options="accountOptions"
                placeholder="Select Account"
                size="sm"
                required
              />
            </div>

            <!-- Debit -->
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">
                Debit
              </label>
              <input
                type="number"
                v-model="account.debit"
                step="0.01"
                class="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                placeholder="0.00"
              />
            </div>

            <!-- Credit -->
            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">
                Credit
              </label>
              <input
                type="number"
                v-model="account.credit"
                step="0.01"
                class="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                placeholder="0.00"
              />
            </div>
          </div>

          <!-- Add Account Button -->
          <Button
            type="button"
            variant="outline"
            size="sm"
            @click="addAccount"
          >
            <FeatherIcon name="plus" class="w-4 h-4 mr-1" />
            Add Account
          </Button>
        </div>
      </div>

      <!-- Total Summary -->
      <div class="bg-gray-50 rounded-lg p-4">
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span class="text-gray-500">Total Debit:</span>
            <span class="ml-2 font-medium">{{ formatCurrency(totalDebit) }}</span>
          </div>
          <div>
            <span class="text-gray-500">Total Credit:</span>
            <span class="ml-2 font-medium">{{ formatCurrency(totalCredit) }}</span>
          </div>
          <div class="col-span-2">
            <span class="text-gray-500">Difference:</span>
            <span 
              class="ml-2 font-medium"
              :class="difference === 0 ? 'text-green-600' : 'text-red-600'"
            >
              {{ formatCurrency(difference) }}
            </span>
          </div>
        </div>
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
          :disabled="!isValid"
        >
          Create Journal Entry
        </Button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useReconciliation } from '@/composables/useReconciliation'
import { formatCurrency } from '@/utils/formatters'

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
const { createJournalEntry, creatingJournal } = useReconciliation()

// Form data
const form = ref({
  posting_date: '',
  reference_no: '',
  user_remark: '',
  accounts: []
})

const accountOptions = ref([])

// Computed
const creating = computed(() => creatingJournal.value)

const totalDebit = computed(() => {
  return form.value.accounts.reduce((sum, account) => sum + (parseFloat(account.debit) || 0), 0)
})

const totalCredit = computed(() => {
  return form.value.accounts.reduce((sum, account) => sum + (parseFloat(account.credit) || 0), 0)
})

const difference = computed(() => {
  return totalDebit.value - totalCredit.value
})

const isValid = computed(() => {
  return form.value.posting_date && 
         form.value.accounts.length >= 2 && 
         Math.abs(difference.value) < 0.01 &&
         form.value.accounts.every(account => account.account)
})

// Methods
const loadAccounts = async () => {
  try {
    const result = await frappe.call({
      method: 'frappe.client.get_list',
      args: {
        doctype: 'Account',
        filters: { is_group: 0 },
        fields: ['name', 'account_name', 'account'],
        order_by: 'account_name'
      }
    })
    
    accountOptions.value = result.message.map(account => ({
      label: `${account.account_name} (${account.account})`,
      value: account.name
    }))
  } catch (error) {
    console.error('Error loading accounts:', error)
    accountOptions.value = []
  }
}

const addAccount = () => {
  form.value.accounts.push({
    account: '',
    debit: 0,
    credit: 0
  })
}

const removeAccount = (index) => {
  form.value.accounts.splice(index, 1)
}

const handleSubmit = async () => {
  if (!isValid.value) return
  
  try {
    const journalData = {
      ...form.value,
      company: props.bankTransaction.company,
      accounts: form.value.accounts.map(account => ({
        ...account,
        debit: parseFloat(account.debit) || 0,
        credit: parseFloat(account.credit) || 0
      }))
    }
    
    const result = await createJournalEntry(journalData)
    emit('created', result)
  } catch (error) {
    console.error('Error creating journal entry:', error)
  }
}

const initializeForm = () => {
  if (props.bankTransaction) {
    form.value.posting_date = props.bankTransaction.date
    form.value.reference_no = props.bankTransaction.reference || ''
    form.value.user_remark = props.bankTransaction.description || ''
    
    // Initialize with two accounts (bank account and a default account)
    form.value.accounts = [
      {
        account: props.bankTransaction.bank_account,
        debit: props.bankTransaction.amount > 0 ? Math.abs(props.bankTransaction.amount) : 0,
        credit: props.bankTransaction.amount < 0 ? Math.abs(props.bankTransaction.amount) : 0
      },
      {
        account: '',
        debit: props.bankTransaction.amount < 0 ? Math.abs(props.bankTransaction.amount) : 0,
        credit: props.bankTransaction.amount > 0 ? Math.abs(props.bankTransaction.amount) : 0
      }
    ]
  }
}

// Lifecycle
onMounted(() => {
  loadAccounts()
  initializeForm()
})
</script> 