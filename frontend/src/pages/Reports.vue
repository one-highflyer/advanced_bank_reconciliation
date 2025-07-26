<template>
  <div class="min-h-screen bg-gray-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Header -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900">
          Reconciliation Reports
        </h1>
        <p class="mt-2 text-sm text-gray-600">
          View and analyze bank reconciliation reports
        </p>
      </div>

      <!-- Filters -->
      <div class="bg-white shadow rounded-lg p-6 mb-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          Report Filters
        </h3>
        
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Company
            </label>
            <Select
              v-model="filters.company"
              :options="companyOptions"
              placeholder="Select Company"
              @update:model-value="loadBankAccounts"
            />
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Bank Account
            </label>
            <Select
              v-model="filters.bankAccount"
              :options="bankAccountOptions"
              placeholder="Select Bank Account"
            />
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              From Date
            </label>
            <input
              type="date"
              v-model="filters.fromDate"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              To Date
            </label>
            <input
              type="date"
              v-model="filters.toDate"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
        
        <div class="mt-4 flex justify-end">
          <Button
            @click="generateReport"
            :loading="loading"
            class="mr-2"
          >
            Generate Report
          </Button>
          
          <Button
            v-if="reportData"
            variant="outline"
            @click="exportReport"
          >
            Export
          </Button>
        </div>
      </div>

      <!-- Report Results -->
      <div v-if="reportData">
        <!-- Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <NumberCard
            title="Total Transactions"
            :value="reportData.totalTransactions"
            variant="info"
          />
          <NumberCard
            title="Reconciled Transactions"
            :value="reportData.reconciledTransactions"
            variant="success"
          />
          <NumberCard
            title="Unreconciled Transactions"
            :value="reportData.unreconciledTransactions"
            variant="warning"
          />
          <NumberCard
            title="Reconciliation Rate"
            :value="`${reportData.reconciliationRate}%`"
            variant="default"
          />
        </div>

        <!-- Detailed Report Table -->
        <div class="bg-white shadow rounded-lg">
          <div class="px-6 py-4 border-b border-gray-200">
            <h3 class="text-lg font-medium text-gray-900">
              Detailed Report
            </h3>
          </div>
          
          <div class="overflow-x-auto">
            <ListView
              :columns="reportColumns"
              :data="reportData.details"
              :loading="loading"
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
            </ListView>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div 
        v-else-if="!loading"
        class="text-center py-12"
      >
        <FeatherIcon 
          name="bar-chart-2" 
          class="mx-auto h-12 w-12 text-gray-400"
        />
        <h3 class="mt-2 text-sm font-medium text-gray-900">
          No report data
        </h3>
        <p class="mt-1 text-sm text-gray-500">
          Select filters and generate a report to view data.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { formatDate, formatCurrency } from '@/utils/formatters'
import NumberCard from '@/components/NumberCard.vue'
import { useFilters } from '@/composables/useFilters'

// Composables
const { companies, bankAccounts, loadCompanies, loadBankAccounts } = useFilters()

// Local state
const filters = reactive({
  company: '',
  bankAccount: '',
  fromDate: '',
  toDate: ''
})

const loading = ref(false)
const reportData = ref(null)

// Computed
const companyOptions = computed(() => {
  return companies.value.map(company => ({
    label: company.company_name || company.name,
    value: company.name
  }))
})

const bankAccountOptions = computed(() => {
  if (!filters.company) return []
  
  return bankAccounts.value
    .filter(account => account.company === filters.company)
    .map(account => ({
      label: `${account.account_name} (${account.account})`,
      value: account.name
    }))
})

const reportColumns = computed(() => [
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
    key: 'reconciled_date',
    label: 'Reconciled Date',
    sortable: true
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

const generateReport = async () => {
  if (!filters.company || !filters.bankAccount || !filters.fromDate || !filters.toDate) {
    return
  }
  
  loading.value = true
  try {
    const result = await frappe.call({
      method: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.get_reconciliation_report',
      args: {
        company: filters.company,
        bank_account: filters.bankAccount,
        from_date: filters.fromDate,
        to_date: filters.toDate
      }
    })
    
    reportData.value = result.message
  } catch (error) {
    console.error('Error generating report:', error)
    reportData.value = null
  } finally {
    loading.value = false
  }
}

const exportReport = () => {
  if (!reportData.value) return
  
  // Export logic here
  console.log('Exporting report:', reportData.value)
}

// Load initial data
onMounted(async () => {
  await loadCompanies()
  if (filters.company) {
    await loadBankAccounts(filters.company)
  }
})

// Watch for company changes
watch(() => filters.company, async (newCompany) => {
  if (newCompany) {
    await loadBankAccounts(newCompany)
  }
})
</script> 