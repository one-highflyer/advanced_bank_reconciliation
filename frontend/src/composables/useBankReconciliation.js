import { ref, computed } from 'vue'
import { 
  unreconciledTransactions,
  reconciliationSummary,
  validateBankTransactionsResource,
  uploadBankStatement,
  autoReconcileVouchers,
  batchValidateUnvalidatedTransactions
} from '@/services/bankReconciliation'

/**
 * Composable for managing bank reconciliation data and operations
 * Following the same pattern as helpdesk app
 */
export function useBankReconciliation() {
  // Reactive state
  const selectedTransactions = ref([])
  const uploading = ref(false)
  const autoReconciling = ref(false)
  const error = ref(null)

  // Computed properties
  const transactions = computed(() => unreconciledTransactions.data || [])
  const summary = computed(() => reconciliationSummary.data || {
    openingBalance: 0,
    clearedBalance: 0,
    difference: 0,
    currency: 'USD'
  })

  const hasTransactions = computed(() => transactions.value.length > 0)
  
  const totalAmount = computed(() => {
    return transactions.value.reduce((sum, transaction) => sum + Math.abs(transaction.amount), 0)
  })

  const selectedAmount = computed(() => {
    return selectedTransactions.value.reduce((sum, transaction) => sum + Math.abs(transaction.amount), 0)
  })

  const loading = computed(() => {
    return unreconciledTransactions.loading || 
           reconciliationSummary.loading || 
           validateBankTransactionsResource.loading
  })

  // Methods
  const getUnreconciledEntries = async (filters = {}) => {
    error.value = null
    
    try {
      // Update both resources with the same filters
      unreconciledTransactions.update({ params: filters })
      reconciliationSummary.update({ params: filters })
      
      // Fetch both in parallel
      await Promise.all([
        unreconciledTransactions.fetch(),
        reconciliationSummary.fetch()
      ])
    } catch (err) {
      error.value = err.message || 'Failed to load unreconciled entries'
      console.error('Error loading unreconciled entries:', err)
    }
  }

  const uploadStatement = async (file) => {
    uploading.value = true
    error.value = null
    
    try {
      const result = await uploadBankStatement({ file })
      
      // Refresh data after successful upload
      await getUnreconciledEntries()
      
      return result
    } catch (err) {
      error.value = err.message || 'Failed to upload bank statement'
      console.error('Error uploading bank statement:', err)
      throw err
    } finally {
      uploading.value = false
    }
  }

  const autoReconcile = async (filters = {}) => {
    autoReconciling.value = true
    error.value = null
    
    try {
      const result = await autoReconcileVouchers(filters)
      
      // Refresh data after successful auto-reconciliation
      await getUnreconciledEntries(filters)
      
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
      await getUnreconciledEntries(filters)
      
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
      await getUnreconciledEntries(filters)
      
      return result
    } catch (err) {
      error.value = err.message || 'Failed to batch validate'
      console.error('Error batch validating:', err)
      throw err
    }
  }

  const selectTransaction = (transactionName, selected = true) => {
    if (selected) {
      const transaction = transactions.value.find(t => t.name === transactionName)
      if (transaction && !selectedTransactions.value.find(t => t.name === transactionName)) {
        selectedTransactions.value.push(transaction)
      }
    } else {
      selectedTransactions.value = selectedTransactions.value.filter(t => t.name !== transactionName)
    }
  }

  const selectAllTransactions = (selected = true) => {
    if (selected) {
      selectedTransactions.value = [...transactions.value]
    } else {
      selectedTransactions.value = []
    }
  }

  const clearSelection = () => {
    selectedTransactions.value = []
  }

  const refreshData = async (filters = {}) => {
    await getUnreconciledEntries(filters)
  }

  const clearError = () => {
    error.value = null
  }

  const reset = () => {
    selectedTransactions.value = []
    error.value = null
    uploading.value = false
    autoReconciling.value = false
    unreconciledTransactions.reset()
    reconciliationSummary.reset()
    validateBankTransactionsResource.reset()
  }

  return {
    // State
    selectedTransactions,
    uploading,
    autoReconciling,
    error,
    
    // Computed
    transactions,
    summary,
    hasTransactions,
    totalAmount,
    selectedAmount,
    loading,
    
    // Methods
    getUnreconciledEntries,
    uploadStatement,
    autoReconcile,
    validateTransactions,
    batchValidate,
    selectTransaction,
    selectAllTransactions,
    clearSelection,
    refreshData,
    clearError,
    reset
  }
} 