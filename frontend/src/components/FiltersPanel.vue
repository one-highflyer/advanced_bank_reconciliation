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
        <Autocomplete :model-value="selectedCompanyOption" @update:model-value="(value) => {
          setCompany(value?.value || value);
          handleFilterChange();
        }" :options="companyOptions" placeholder="Select Company" />
      </div>

      <!-- Bank Account Filter -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Bank Account
        </label>
        <Autocomplete :model-value="selectedBankAccountOption" @update:model-value="(value) => {
          setBankAccount(value?.value || value);
          handleFilterChange();
        }" :options="bankAccountOptions" placeholder="Select Bank Account" :disabled="!selectedCompanyOption?.value" />
      </div>

      <!-- Date Range -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          From Date
        </label>
        <DatePicker :model-value="dateRange.from" @update:model-value="(value) => {
          setDateRange({ ...dateRange, from: value });
          handleFilterChange();
        }" />
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          To Date
        </label>
        <DatePicker :model-value="dateRange.to" @update:model-value="(value) => {
          setDateRange({ ...dateRange, to: value });
          handleFilterChange();
        }" />
      </div>
    </div>

    <!-- Additional Options -->
    <div class="mt-4 flex items-center justify-between space-x-6">
      <Button variant="outline" size="sm" @click="clearFilters">
        Clear Filters
      </Button>
      <Button variant="solid" size="sm" @click="handleFilterChange">
        Get Unreconciled Entries
      </Button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Autocomplete, Button, DatePicker } from 'frappe-ui'
import { useFilters } from '../composables/useFilters'

// Emits
const emit = defineEmits([
  'filter-change'
])

// Composables
const {
  selectedCompany,
  selectedBankAccount,
  dateRange,
  companyOptions,
  bankAccountOptions,
  setCompany,
  setBankAccount,
  setDateRange
} = useFilters()

// Computed properties for selected options
const selectedCompanyOption = computed(() => {
  if (!selectedCompany.value) return ""
  const option = companyOptions.value.find(option => option.value === selectedCompany.value)
  return option || ""
})

const selectedBankAccountOption = computed(() => {
  if (!selectedBankAccount.value) return ""
  const option = bankAccountOptions.value.find(option => option.value === selectedBankAccount.value)
  return option || ""
})

const handleFilterChange = () => {
  console.log('handleFilterChange', selectedCompany.value, selectedBankAccount.value, dateRange.value.from, dateRange.value.to)
  emit('filter-change', {
    company: selectedCompany.value,
    bankAccount: selectedBankAccount.value,
    fromDate: dateRange.value.from,
    toDate: dateRange.value.to
  })
}

const clearFilters = () => {
  setCompany('')
  setBankAccount('')
  setDateRange({ from: '', to: '' })
  // Trigger filter change after clearing
  setTimeout(() => {
    handleFilterChange()
  }, 0)
}
</script>