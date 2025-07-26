import { ref, computed } from 'vue'
import * as bankReconciliationAPI from '../services/bankReconciliation'

/**
 * Composable for bank reconciliation functionality
 * Provides reactive state and methods for reconciliation workflows
 */
export function useReconciliation() {
  // Loading states
  const isLoading = ref(false)
  const isSearching = ref(false)
  const isReconciling = ref(false)
  const isCreatingVoucher = ref(false)
  const isUpdating = ref(false)

  // Error state
  const error = ref(null)
  const lastError = ref(null)

  // Data state
  const availableVouchers = ref([])
  const selectedVouchers = ref([])

  // Helper to clear error state
  const clearError = () => {
    error.value = null
  }

  // Helper to handle errors
  const handleError = (err, context = '') => {
    console.error(`Error in ${context}:`, err)
    error.value = err
    lastError.value = {
      message: err.message || 'An error occurred',
      context,
      timestamp: new Date()
    }
    throw err
  }

  /**
   * Search for vouchers that can be matched against a bank transaction
   */
  const searchVouchers = async (searchParams) => {
    isSearching.value = true
    isLoading.value = true
    clearError()

    try {
      console.log('useReconciliation: Searching vouchers with params:', searchParams)
      const result = await bankReconciliationAPI.searchVouchers(searchParams)
      
      // Transform the API response if needed
      availableVouchers.value = result || []
      console.log('useReconciliation: Found vouchers:', availableVouchers.value.length)
      
      return availableVouchers.value
    } catch (err) {
      availableVouchers.value = []
      handleError(err, 'searchVouchers')
    } finally {
      isSearching.value = false
      isLoading.value = false
    }
  }

  /**
   * Reconcile selected vouchers with a bank transaction
   */
  const reconcileVouchers = async (bankTransactionName, vouchers) => {
    isReconciling.value = true
    isLoading.value = true
    clearError()

    try {
      console.log('useReconciliation: Reconciling vouchers:', { bankTransactionName, vouchers })
      const result = await bankReconciliationAPI.reconcileVouchers(bankTransactionName, vouchers)
      
      // Clear selected vouchers after successful reconciliation
      selectedVouchers.value = []
      console.log('useReconciliation: Reconciliation successful')
      
      return result
    } catch (err) {
      handleError(err, 'reconcileVouchers')
    } finally {
      isReconciling.value = false
      isLoading.value = false
    }
  }

  /**
   * Create payment entries for unpaid invoices
   */
  const createPaymentEntriesForInvoices = async (bankTransactionName, invoices, autoReconcile = false) => {
    isCreatingVoucher.value = true
    isLoading.value = true
    clearError()

    try {
      console.log('useReconciliation: Creating payment entries for invoices:', { 
        bankTransactionName, 
        invoices, 
        autoReconcile 
      })
      
      const result = await bankReconciliationAPI.createPaymentEntriesForInvoices(
        bankTransactionName, 
        invoices, 
        autoReconcile
      )
      
      console.log('useReconciliation: Payment entries created successfully')
      return result
    } catch (err) {
      handleError(err, 'createPaymentEntriesForInvoices')
    } finally {
      isCreatingVoucher.value = false
      isLoading.value = false
    }
  }

  /**
   * Create a new payment entry
   */
  const createPaymentEntry = async (paymentData) => {
    isCreatingVoucher.value = true
    isLoading.value = true
    clearError()

    try {
      console.log('useReconciliation: Creating payment entry:', paymentData)
      const result = await bankReconciliationAPI.createPaymentEntry(paymentData)
      
      console.log('useReconciliation: Payment entry created successfully')
      return result
    } catch (err) {
      handleError(err, 'createPaymentEntry')
    } finally {
      isCreatingVoucher.value = false
      isLoading.value = false
    }
  }

  /**
   * Create a new journal entry
   */
  const createJournalEntry = async (journalData) => {
    isCreatingVoucher.value = true
    isLoading.value = true
    clearError()

    try {
      console.log('useReconciliation: Creating journal entry:', journalData)
      const result = await bankReconciliationAPI.createJournalEntry(journalData)
      
      console.log('useReconciliation: Journal entry created successfully')
      return result
    } catch (err) {
      handleError(err, 'createJournalEntry')
    } finally {
      isCreatingVoucher.value = false
      isLoading.value = false
    }
  }

  /**
   * Update bank transaction details
   */
  const updateBankTransaction = async (updateData) => {
    isUpdating.value = true
    isLoading.value = true
    clearError()

    try {
      console.log('useReconciliation: Updating bank transaction:', updateData)
      const result = await bankReconciliationAPI.updateBankTransaction(updateData)
      
      console.log('useReconciliation: Bank transaction updated successfully')
      return result
    } catch (err) {
      handleError(err, 'updateBankTransaction')
    } finally {
      isUpdating.value = false
      isLoading.value = false
    }
  }

  /**
   * Get available document types for reconciliation
   */
  const getDocumentTypes = async () => {
    isLoading.value = true
    clearError()

    try {
      const result = await bankReconciliationAPI.getDocumentTypesForReconciliation()
      console.log('useReconciliation: Document types retrieved:', result)
      return result
    } catch (err) {
      handleError(err, 'getDocumentTypes')
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Get bank transaction details
   */
  const getBankTransactionDetails = async (bankTransactionName) => {
    isLoading.value = true
    clearError()

    try {
      const result = await bankReconciliationAPI.getBankTransactionDetails(bankTransactionName)
      console.log('useReconciliation: Bank transaction details retrieved:', result)
      return result
    } catch (err) {
      handleError(err, 'getBankTransactionDetails')
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Complex reconciliation workflow that handles mixed voucher types
   * This implements the sophisticated logic from dialog_manager.js
   */
  const processComplexReconciliation = async (bankTransactionName, vouchers) => {
    isReconciling.value = true
    isLoading.value = true
    clearError()

    try {
      console.log('useReconciliation: Processing complex reconciliation:', { 
        bankTransactionName, 
        vouchers: vouchers.length 
      })

      // Separate unpaid invoices from regular vouchers
      const unpaidInvoices = vouchers.filter(v => 
        v.doctype === 'Unpaid Sales Invoice' || v.doctype === 'Unpaid Purchase Invoice'
      )
      const regularVouchers = vouchers.filter(v => 
        v.doctype !== 'Unpaid Sales Invoice' && v.doctype !== 'Unpaid Purchase Invoice'
      )

      console.log('Separated vouchers:', {
        unpaidInvoices: unpaidInvoices.length,
        regularVouchers: regularVouchers.length
      })

      let finalResult = null

      // Step 1: Process unpaid invoices first if any
      if (unpaidInvoices.length > 0) {
        const invoiceData = unpaidInvoices.map(invoice => ({
          doctype: invoice.doctype,
          name: invoice.name,
          allocated_amount: invoice.amount
        }))

        // Auto-reconcile if only unpaid invoices, otherwise just create payment entries
        const autoReconcile = regularVouchers.length === 0
        
        console.log('Creating payment entries for unpaid invoices, auto-reconcile:', autoReconcile)
        finalResult = await createPaymentEntriesForInvoices(
          bankTransactionName,
          invoiceData,
          autoReconcile
        )
      }

      // Step 2: Process regular vouchers if any
      if (regularVouchers.length > 0) {
        const voucherData = regularVouchers.map(voucher => ({
          payment_doctype: voucher.doctype,
          payment_name: voucher.name,
          amount: voucher.amount
        }))

        console.log('Reconciling regular vouchers')
        finalResult = await reconcileVouchers(bankTransactionName, voucherData)
      }

      // Clear selections after successful processing
      selectedVouchers.value = []
      availableVouchers.value = []

      console.log('useReconciliation: Complex reconciliation completed successfully')
      return finalResult

    } catch (err) {
      handleError(err, 'processComplexReconciliation')
    } finally {
      isReconciling.value = false
      isLoading.value = false
    }
  }

  // Computed states
  const hasError = computed(() => error.value !== null)
  const isAnyLoading = computed(() => 
    isLoading.value || isSearching.value || isReconciling.value || 
    isCreatingVoucher.value || isUpdating.value
  )

  // Reset all state
  const resetState = () => {
    availableVouchers.value = []
    selectedVouchers.value = []
    error.value = null
    lastError.value = null
  }

  return {
    // State
    isLoading,
    isSearching,
    isReconciling,
    isCreatingVoucher,
    isUpdating,
    error,
    lastError,
    hasError,
    isAnyLoading,
    availableVouchers,
    selectedVouchers,

    // Methods
    searchVouchers,
    reconcileVouchers,
    createPaymentEntriesForInvoices,
    createPaymentEntry,
    createJournalEntry,
    updateBankTransaction,
    getDocumentTypes,
    getBankTransactionDetails,
    processComplexReconciliation,
    clearError,
    resetState
  }
} 