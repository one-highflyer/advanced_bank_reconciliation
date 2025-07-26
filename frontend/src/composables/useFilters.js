import { ref, computed, watch, onMounted } from 'vue'
import { companies, bankAccounts } from '../services/bankReconciliation'

/**
 * Composable for managing filter data and state
 * Following the same pattern as helpdesk app
 */
export function useFilters() {
  // Reactive state
  const selectedCompany = ref('')
  const selectedBankAccount = ref('')
  const dateRange = ref({ from: '', to: '' })
  const error = ref(null)

  // Computed properties
  const companyOptions = computed(() => {
    return companies.data?.map(company => ({
      label: company.company_name || company.name,
      value: company.name
    })) || []
  })

  const bankAccountOptions = computed(() => {
    if (!selectedCompany.value) return []
    
    return bankAccounts.data?.map(account => ({
      label: `${account.account_name} (${account.account})`,
      value: account.name
    })) || []
  })

  const loading = computed(() => {
    return companies.loading || bankAccounts.loading
  })

  // Methods
  const loadCompanies = async () => {
    if (companies.fetched) return // Already loaded
    
    error.value = null
    try {
      await companies.fetch()
    } catch (err) {
      error.value = err.message || 'Failed to load companies'
      console.error('Error loading companies:', err)
    }
  }

  const loadBankAccounts = async (company) => {
    if (!company) {
      bankAccounts.reset()
      return
    }
    
    error.value = null
    try {
      bankAccounts.update({
        filters: {
          company: company,
          is_company_account: 1
        }
      })
      await bankAccounts.fetch()
    } catch (err) {
      error.value = err.message || 'Failed to load bank accounts'
      console.error('Error loading bank accounts:', err)
    }
  }

  const setCompany = (company) => {
    selectedCompany.value = company
    if (!company) {
      selectedBankAccount.value = ''
    }
  }

  const setBankAccount = (account) => {
    selectedBankAccount.value = account
  }

  const setDateRange = (range) => {
    dateRange.value = range
  }

  const clearError = () => {
    error.value = null
  }

  const reset = () => {
    selectedCompany.value = ''
    selectedBankAccount.value = ''
    error.value = null
    companies.reset()
    bankAccounts.reset()
  }

  // Watch for company changes to reset bank account
  watch(selectedCompany, (newCompany) => {
    if (newCompany) {
      console.log('Loading bank accounts for company:', newCompany);
      loadBankAccounts(newCompany)
    }
    selectedBankAccount.value = ''
  })

  onMounted(async () => {
    await loadCompanies()
  })

  return {
    // State
    selectedCompany,
    selectedBankAccount,
    dateRange,
    error,
    
    // Computed
    companies: computed(() => companies.data || []),
    bankAccounts: computed(() => bankAccounts.data || []),
    companyOptions,
    bankAccountOptions,
    loading,
    
    // Methods
    loadCompanies,
    loadBankAccounts,
    setCompany,
    setBankAccount,
    setDateRange,
    clearError,
    reset
  }
} 