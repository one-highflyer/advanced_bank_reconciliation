<template>
  <div class="bg-white shadow rounded-lg p-6 mb-6">
    <h3 class="text-lg font-medium text-gray-900 mb-4">
      Filters
    </h3>
    
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Company Filter -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Company
        </label>
        <Select
          :model-value="company"
          @update:model-value="(value) => { emit('update:company', value); handleFilterChange(); }"
          :options="companyOptions"
          placeholder="Select Company"
        />
      </div>

      <!-- Bank Account Filter -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Bank Account
        </label>
        <Select
          :model-value="bankAccount"
          @update:model-value="(value) => { emit('update:bankAccount', value); handleFilterChange(); }"
          :options="bankAccountOptions"
          placeholder="Select Bank Account"
          :disabled="!company"
        />
      </div>

      <!-- Date Range -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          From Date
        </label>
        <input
          type="date"
          :value="dateRange.from"
          @input="(event) => { emit('update:dateRange', { ...dateRange, from: event.target.value }); handleFilterChange(); }"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          To Date
        </label>
        <input
          type="date"
          :value="dateRange.to"
          @input="(event) => { emit('update:dateRange', { ...dateRange, to: event.target.value }); handleFilterChange(); }"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
    </div>

    <!-- Additional Options -->
    <div class="mt-4 flex items-center space-x-6">
      <label class="flex items-center">
        <input
          type="checkbox"
          :checked="useReferenceDate"
          @change="(event) => { emit('update:useReferenceDate', event.target.checked); handleFilterChange(); }"
          class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        <span class="ml-2 text-sm text-gray-700">
          Use Reference Date
        </span>
      </label>
      
      <Button
        variant="outline"
        size="sm"
        @click="clearFilters"
      >
        Clear Filters
      </Button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useFilters } from '@/composables/useFilters'

// Props
const props = defineProps({
  company: {
    type: String,
    default: ''
  },
  bankAccount: {
    type: String,
    default: ''
  },
  dateRange: {
    type: Object,
    default: () => ({ from: '', to: '' })
  },
  useReferenceDate: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits([
  'update:company',
  'update:bankAccount', 
  'update:dateRange',
  'update:useReferenceDate',
  'filter-change'
])

// Composables
const { companies, bankAccounts, loading } = useFilters()

// Computed
const companyOptions = computed(() => {
  return companies.value.map(company => ({
    label: company.name,
    value: company.name
  }))
})

const bankAccountOptions = computed(() => {
  if (!props.company) return []
  
  return bankAccounts.value
    .filter(account => account.company === props.company)
    .map(account => ({
      label: `${account.account_name} (${account.account})`,
      value: account.name
    }))
})

// Event handlers
const handleFilterChange = () => {
  emit('filter-change', {
    company: props.company,
    bankAccount: props.bankAccount,
    dateRange: props.dateRange,
    useReferenceDate: props.useReferenceDate
  })
}

const clearFilters = () => {
  emit('update:company', '')
  emit('update:bankAccount', '')
  emit('update:dateRange', { from: '', to: '' })
  emit('update:useReferenceDate', false)
  
  // Trigger filter change after clearing
  setTimeout(() => {
    handleFilterChange()
  }, 0)
}

// Watch for company changes to reset bank account
watch(() => props.company, (newCompany) => {
  if (!newCompany) {
    emit('update:bankAccount', '')
  }
})
</script> 