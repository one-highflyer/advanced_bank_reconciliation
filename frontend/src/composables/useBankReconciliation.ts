import { ref, computed, reactive } from 'vue'
import {
  pendingTransactions,
  getReconciledTransactions,
  validateBankTransactionsResource,
  uploadBankStatement,
  autoReconcileVouchers,
  batchValidateUnvalidatedTransactions,
  getAccountBalance
} from '../services/bankReconciliation'

type BankReconciliationFilters = {
  company: string
  bank_account: string
  from_date: string
  to_date: string
}

/**
 * Composable for managing bank reconciliation data and operations
 * Following the same pattern as helpdesk app
 */
export function useBankReconciliation() {
  // Reactive state
  const reconciledTransactions = ref([])
  const uploading = ref(false)
  const autoReconciling = ref(false)
  const error = ref(null)
  const summary = reactive({
    openingBalance: 0,
    clearedBalance: 0,
    difference: 0,
    currency: 'NZD'
  })

  // Computed properties
  const unreconciledTransactions = computed(() => pendingTransactions.data || [])

  const hasTransactions = computed(() => unreconciledTransactions.value.length > 0)

  // Methods
  const getUnreconciledEntries = async (filters: BankReconciliationFilters) => {
    error.value = null

    try {
      console.log('Fetching unreconciled entries with filters:', filters)
      console.log('pendingTransactions before update:', pendingTransactions.data)
      
      // Update both resources with the same filters
      pendingTransactions.update({ params: filters })
      console.log('pendingTransactions after update:', pendingTransactions.data)
      
      await pendingTransactions.fetch()
      console.log('pendingTransactions after fetch:', pendingTransactions.data)
      console.log('pendingTransactions.data type:', typeof pendingTransactions.data)
      console.log('pendingTransactions.data length:', pendingTransactions.data?.length)
      if (pendingTransactions.data?.length > 0) {
        console.log('Unreconciled entries fetched', pendingTransactions.data[0])
        return
      }

      const reconciledTransactionsResponse = await getReconciledTransactions(filters)
      reconciledTransactions.value = reconciledTransactionsResponse.message

      console.log('Unreconciled entries fetched', pendingTransactions.data)
      console.log('Reconciled entries fetched', reconciledTransactions.value)

      // Get account balance
      const closingBalence = await getAccountBalance(filters.bank_account, filters.company, filters.to_date)
      const openingBalence = await getAccountBalance(filters.bank_account, filters.company, filters.from_date)
      summary.openingBalance = openingBalence
      summary.clearedBalance = closingBalence
      summary.difference = closingBalence - openingBalence
      console.log('Bank account summary', filters.bank_account, summary)
    } catch (err) {
      error.value = err.message || 'Failed to load unreconciled entries'
      console.error('Error loading unreconciled entries:', err)
    }
  }

  const autoReconcile = async (filters = {}) => {
    autoReconciling.value = true
    error.value = null

    try {
      const result = await autoReconcileVouchers(filters)

      // Refresh data after successful auto-reconciliation
      // await getUnreconciledEntries(filters)

      return result
    } catch (err) {
      error.value = err.message || 'Failed to auto reconcile'
      console.error('Error auto reconciling:', err)
      throw err
    } finally {
      autoReconciling.value = false
    }
  }

  const validateTransactions = async (filters = {}) => {
    error.value = null

    try {
      validateBankTransactionsResource.update({ params: filters })
      const result = await validateBankTransactionsResource.fetch()

      // Refresh data after successful validation
      // await getUnreconciledEntries(filters)

      return result
    } catch (err) {
      error.value = err.message || 'Failed to validate transactions'
      console.error('Error validating transactions:', err)
      throw err
    }
  }

  const batchValidate = async (filters = {}) => {
    error.value = null

    try {
      const result = await batchValidateUnvalidatedTransactions(filters)

      // Refresh data after successful batch validation
      // await getUnreconciledEntries(filters)

      return result
    } catch (err) {
      error.value = err.message || 'Failed to batch validate'
      console.error('Error batch validating:', err)
      throw err
    }
  }

  const refreshData = async (filters = {}) => {
    // await getUnreconciledEntries(filters)
  }

  const clearError = () => {
    error.value = null
  }

  const reset = () => {
    error.value = null
    uploading.value = false
    autoReconciling.value = false
    reconciledTransactions.value = []
    pendingTransactions.reset()
  }

  return {
    // State
    uploading,
    autoReconciling,
    error,

    // Computed
    unreconciledTransactions,
    reconciledTransactions,
    summary,
    hasTransactions,

    // Methods
    getUnreconciledEntries,
    autoReconcile,
    validateTransactions,
    batchValidate,
    refreshData,
    clearError,
    reset
  }
} 