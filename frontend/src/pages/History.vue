<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <div class="bg-white shadow-sm border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-4">
          <div>
            <h1 class="text-2xl font-semibold text-gray-900">
              Reconciliation History
            </h1>
            <p class="text-sm text-gray-600">
              View history of bank reconciliation activities
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Filters -->
      <div class="bg-white shadow rounded-lg p-6 mb-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">
          History Filters
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
              :disabled="!filters.company"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Activity Type
            </label>
            <Select
              v-model="filters.activityType"
              :options="activityTypeOptions"
              placeholder="All Activities"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Date Range
            </label>
            <Select
              v-model="filters.dateRange"
              :options="dateRangeOptions"
              placeholder="Select Date Range"
            />
          </div>
        </div>

        <div class="flex justify-end mt-4">
          <Button
            @click="loadHistory"
            :loading="loading"
          >
            Load History
          </Button>
        </div>
      </div>

      <!-- History Timeline -->
      <div v-if="historyData.length > 0" class="space-y-6">
        <div class="bg-white shadow rounded-lg">
          <div class="px-6 py-4 border-b border-gray-200">
            <h3 class="text-lg font-medium text-gray-900">
              Reconciliation Activities
            </h3>
          </div>
          
          <div class="p-6">
            <div class="flow-root">
              <ul class="-mb-8">
                <li 
                  v-for="(activity, index) in historyData" 
                  :key="activity.id"
                  class="relative pb-8"
                >
                  <div v-if="index !== historyData.length - 1" class="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true"></div>
                  
                  <div class="relative flex space-x-3">
                    <div>
                      <span 
                        class="h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white"
                        :class="activityIconClasses(activity.type)"
                      >
                        <FeatherIcon 
                          :name="activityIcon(activity.type)" 
                          class="h-5 w-5 text-white"
                        />
                      </span>
                    </div>
                    
                    <div class="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                      <div>
                        <p class="text-sm text-gray-500">
                          {{ activity.description }}
                          <span v-if="activity.user" class="font-medium text-gray-900">
                            {{ by }} {{ activity.user }}
                          </span>
                        </p>
                        
                        <div v-if="activity.details" class="mt-2 text-sm text-gray-700">
                          <div class="grid grid-cols-2 gap-4">
                            <div v-if="activity.details.transaction">
                              <span class="font-medium">Transaction:</span>
                              <span class="ml-1">{{ activity.details.transaction }}</span>
                            </div>
                            <div v-if="activity.details.amount">
                              <span class="font-medium">Amount:</span>
                              <span class="ml-1">{{ formatCurrency(activity.details.amount, activity.details.currency) }}</span>
                            </div>
                            <div v-if="activity.details.vouchers">
                              <span class="font-medium">Vouchers:</span>
                              <span class="ml-1">{{ activity.details.vouchers.join(', ') }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      <div class="text-right text-sm whitespace-nowrap text-gray-500">
                        <time :datetime="activity.timestamp">
                          {{ formatRelativeTime(activity.timestamp) }}
                        </time>
                      </div>
                    </div>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div 
        v-else-if="!loading"
        class="text-center py-12"
      >
        <FeatherIcon 
          name="clock" 
          class="mx-auto h-12 w-12 text-gray-400"
        />
        <h3 class="mt-2 text-sm font-medium text-gray-900">
          No history found
        </h3>
        <p class="mt-1 text-sm text-gray-500">
          No reconciliation activities found for the selected filters.
        </p>
      </div>

      <!-- Loading State -->
      <div 
        v-if="loading"
        class="text-center py-12"
      >
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p class="mt-2 text-sm text-gray-500">
          Loading history...
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { formatCurrency, formatRelativeTime } from '@/utils/formatters'
import { useFilters } from '@/composables/useFilters'

// Composables
const { companies, bankAccounts, loadCompanies, loadBankAccounts } = useFilters()

// Local state
const filters = reactive({
  company: '',
  bankAccount: '',
  activityType: '',
  dateRange: '7d'
})

const loading = ref(false)
const historyData = ref([])

// Options
const activityTypeOptions = [
  { label: 'All Activities', value: '' },
  { label: 'Reconciliation', value: 'reconciliation' },
  { label: 'Validation', value: 'validation' },
  { label: 'Upload', value: 'upload' },
  { label: 'Auto Reconcile', value: 'auto_reconcile' }
]

const dateRangeOptions = [
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
  { label: 'Last 90 days', value: '90d' },
  { label: 'Last year', value: '1y' },
  { label: 'All time', value: 'all' }
]

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

// Methods
const loadHistory = async () => {
  loading.value = true
  
  try {
    // This would call the actual history API
    // For now, we'll simulate the response
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    historyData.value = [
      {
        id: 1,
        type: 'reconciliation',
        description: 'Reconciled bank transaction with payment entry',
        user: 'John Doe',
        timestamp: '2024-01-15T10:30:00Z',
        details: {
          transaction: 'BANK-TXN-001',
          amount: 1000,
          currency: 'USD',
          vouchers: ['PAY-001']
        }
      },
      {
        id: 2,
        type: 'validation',
        description: 'Validated bank transaction',
        user: 'Jane Smith',
        timestamp: '2024-01-15T09:15:00Z',
        details: {
          transaction: 'BANK-TXN-002',
          amount: -500,
          currency: 'USD'
        }
      },
      {
        id: 3,
        type: 'upload',
        description: 'Uploaded bank statement',
        user: 'Admin User',
        timestamp: '2024-01-14T16:45:00Z',
        details: {
          file: 'statement_jan_2024.csv',
          transactions: 25
        }
      },
      {
        id: 4,
        type: 'auto_reconcile',
        description: 'Auto-reconciled transactions',
        user: 'System',
        timestamp: '2024-01-14T14:20:00Z',
        details: {
          matched: 15,
          total: 25
        }
      }
    ]
  } catch (error) {
    console.error('Error loading history:', error)
  } finally {
    loading.value = false
  }
}

const activityIcon = (type) => {
  const icons = {
    reconciliation: 'link',
    validation: 'check-circle',
    upload: 'upload',
    auto_reconcile: 'refresh-cw'
  }
  return icons[type] || 'activity'
}

const activityIconClasses = (type) => {
  const classes = {
    reconciliation: 'bg-green-500',
    validation: 'bg-blue-500',
    upload: 'bg-purple-500',
    auto_reconcile: 'bg-orange-500'
  }
  return classes[type] || 'bg-gray-500'
}

// Initialize
onMounted(() => {
  loadCompanies()
  loadHistory()
})
</script> 