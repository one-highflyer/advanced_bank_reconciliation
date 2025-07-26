import { ref, computed } from 'vue'
import { 
  linkedVouchers,
  reconcileVouchersResource,
  createPaymentEntryResource,
  createJournalEntryResource,
  validateBankTransactionAsync
} from '@/services/bankReconciliation'

/**
 * Composable for managing reconciliation workflows and voucher selection
 * Following the same pattern as helpdesk app
 */
export function useReconciliation() {
  // Reactive state
  const selectedVouchers = ref([])
  const error = ref(null)

  // Computed properties
  const vouchers = computed(() => linkedVouchers.data || {
    payments: [],
    journals: [],
    invoices: []
  })

  const allVouchers = computed(() => [
    ...vouchers.value.payments,
    ...vouchers.value.journals,
    ...vouchers.value.invoices
  ])

  const hasVouchers = computed(() => {
    return vouchers.value.payments.length > 0 || 
           vouchers.value.journals.length > 0 || 
           vouchers.value.invoices.length > 0
  })

  const totalVouchers = computed(() => {
    return vouchers.value.payments.length + 
           vouchers.value.journals.length + 
           vouchers.value.invoices.length
  })

  const loading = computed(() => {
    return linkedVouchers.loading || 
           reconcileVouchersResource.loading || 
           createPaymentEntryResource.loading || 
           createJournalEntryResource.loading
  })

  // Methods
  const searchVouchers = async (bankTransaction) => {
    if (!bankTransaction) return
    
    error.value = null
    
    try {
      const args = {
        bank_transaction_name: bankTransaction.name,
        amount: bankTransaction.amount,
        date: bankTransaction.date,
        description: bankTransaction.description
      }
      
      linkedVouchers.update({ params: args })
      await linkedVouchers.fetch()
    } catch (err) {
      error.value = err.message || 'Failed to search vouchers'
      console.error('Error searching vouchers:', err)
    }
  }

  const reconcileVouchersWithTransaction = async (bankTransactionName, vouchersToReconcile) => {
    if (!bankTransactionName || !vouchersToReconcile.length) return
    
    error.value = null
    
    try {
      reconcileVouchersResource.update({ 
        params: { 
          bankTransactionName, 
          vouchers: vouchersToReconcile 
        } 
      })
      const result = await reconcileVouchersResource.fetch()
      return result
    } catch (err) {
      error.value = err.message || 'Failed to reconcile vouchers'
      console.error('Error reconciling vouchers:', err)
      throw err
    }
  }

  const createPaymentEntryForTransaction = async (paymentData) => {
    error.value = null
    
    try {
      createPaymentEntryResource.update({ params: paymentData })
      const result = await createPaymentEntryResource.fetch()
      return result
    } catch (err) {
      error.value = err.message || 'Failed to create payment entry'
      console.error('Error creating payment entry:', err)
      throw err
    }
  }

  const createJournalEntryForTransaction = async (journalData) => {
    error.value = null
    
    try {
      createJournalEntryResource.update({ params: journalData })
      const result = await createJournalEntryResource.fetch()
      return result
    } catch (err) {
      error.value = err.message || 'Failed to create journal entry'
      console.error('Error creating journal entry:', err)
      throw err
    }
  }

  const updateTransaction = async (transactionName, updateData) => {
    error.value = null
    
    try {
      // This would use a resource if we had one for updating transactions
      // For now, we'll keep the direct call approach
      const result = await validateBankTransactionAsync(transactionName)
      return result
    } catch (err) {
      error.value = err.message || 'Failed to update transaction'
      console.error('Error updating transaction:', err)
      throw err
    }
  }

  const validateTransaction = async (transactionName) => {
    error.value = null
    
    try {
      const result = await validateBankTransactionAsync(transactionName)
      return result
    } catch (err) {
      error.value = err.message || 'Failed to validate transaction'
      console.error('Error validating transaction:', err)
      throw err
    }
  }

  const clearVouchers = () => {
    selectedVouchers.value = []
    linkedVouchers.reset()
  }

  const clearError = () => {
    error.value = null
  }

  const reset = () => {
    selectedVouchers.value = []
    error.value = null
    linkedVouchers.reset()
    reconcileVouchersResource.reset()
    createPaymentEntryResource.reset()
    createJournalEntryResource.reset()
  }

  return {
    // State
    selectedVouchers,
    error,
    
    // Computed
    vouchers,
    allVouchers,
    hasVouchers,
    totalVouchers,
    loading,
    
    // Methods
    searchVouchers,
    reconcileVouchersWithTransaction,
    createPaymentEntryForTransaction,
    createJournalEntryForTransaction,
    updateTransaction,
    validateTransaction,
    clearVouchers,
    clearError,
    reset
  }
} 