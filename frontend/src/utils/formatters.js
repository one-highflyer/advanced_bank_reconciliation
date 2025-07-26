/**
 * Utility functions for formatting data in the reconciliation components
 */

/**
 * Format a date string or Date object for display
 * @param {string|Date} date - Date to format
 * @param {string} locale - Locale for formatting (defaults to user locale)
 * @returns {string} Formatted date string
 */
export function formatDate(date, locale = 'en-US') {
  if (!date) return '-'
  
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date
    
    // Check if date is valid
    if (isNaN(dateObj.getTime())) {
      return '-'
    }
    
    // Format as MM/DD/YYYY or locale-specific format
    return dateObj.toLocaleDateString(locale, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  } catch (error) {
    console.error('Error formatting date:', error)
    return '-'
  }
}

/**
 * Format a currency amount for display
 * @param {number} amount - Amount to format
 * @param {string} currency - Currency code (e.g., 'USD', 'EUR')
 * @param {string} locale - Locale for formatting
 * @returns {string} Formatted currency string
 */
export function formatCurrency(amount, currency = 'USD', locale = 'en-US') {
  if (amount === null || amount === undefined) return '-'
  
  try {
    const numericAmount = typeof amount === 'string' ? parseFloat(amount) : amount
    
    // Check if amount is a valid number
    if (isNaN(numericAmount)) {
      return '-'
    }
    
    // Use Intl.NumberFormat for proper currency formatting
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(numericAmount)
  } catch (error) {
    console.error('Error formatting currency:', error)
    // Fallback to simple formatting
    return `${currency} ${amount?.toFixed(2) || '0.00'}`
  }
}

/**
 * Format a number for display
 * @param {number} number - Number to format
 * @param {number} decimals - Number of decimal places
 * @param {string} locale - Locale for formatting
 * @returns {string} Formatted number string
 */
export function formatNumber(number, decimals = 2, locale = 'en-US') {
  if (number === null || number === undefined) return '-'
  
  try {
    const numericValue = typeof number === 'string' ? parseFloat(number) : number
    
    if (isNaN(numericValue)) {
      return '-'
    }
    
    return new Intl.NumberFormat(locale, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(numericValue)
  } catch (error) {
    console.error('Error formatting number:', error)
    return number?.toFixed(decimals) || '0.00'
  }
}

/**
 * Format a percentage for display
 * @param {number} value - Value to format as percentage (0.15 = 15%)
 * @param {number} decimals - Number of decimal places
 * @param {string} locale - Locale for formatting
 * @returns {string} Formatted percentage string
 */
export function formatPercentage(value, decimals = 1, locale = 'en-US') {
  if (value === null || value === undefined) return '-'
  
  try {
    const numericValue = typeof value === 'string' ? parseFloat(value) : value
    
    if (isNaN(numericValue)) {
      return '-'
    }
    
    return new Intl.NumberFormat(locale, {
      style: 'percent',
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(numericValue)
  } catch (error) {
    console.error('Error formatting percentage:', error)
    return `${(value * 100).toFixed(decimals)}%`
  }
}

/**
 * Format a file size in bytes to human readable format
 * @param {number} bytes - Size in bytes
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted file size string
 */
export function formatFileSize(bytes, decimals = 1) {
  if (bytes === 0) return '0 Bytes'
  if (!bytes) return '-'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i]
}

/**
 * Truncate text to specified length with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length before truncation
 * @returns {string} Truncated text with ellipsis if needed
 */
export function truncateText(text, maxLength = 50) {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

/**
 * Capitalize the first letter of a string
 * @param {string} text - Text to capitalize
 * @returns {string} Text with first letter capitalized
 */
export function capitalize(text) {
  if (!text) return ''
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase()
}

/**
 * Format a status for display
 * @param {string} status - Status value
 * @returns {string} Formatted status string
 */
export function formatStatus(status) {
  if (!status) return 'Unknown'
  
  // Replace underscores with spaces and capitalize words
  return status
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => capitalize(word))
    .join(' ')
}

/**
 * Get relative time description (e.g., "2 hours ago", "in 3 days")
 * @param {string|Date} date - Date to compare
 * @param {string|Date} baseDate - Base date for comparison (defaults to now)
 * @returns {string} Relative time description
 */
export function getRelativeTime(date, baseDate = new Date()) {
  if (!date) return '-'
  
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date
    const baseDateObj = typeof baseDate === 'string' ? new Date(baseDate) : baseDate
    
    if (isNaN(dateObj.getTime()) || isNaN(baseDateObj.getTime())) {
      return '-'
    }
    
    const diffMs = dateObj.getTime() - baseDateObj.getTime()
    const diffSec = Math.abs(diffMs) / 1000
    const diffMin = diffSec / 60
    const diffHour = diffMin / 60
    const diffDay = diffHour / 24
    
    const isPast = diffMs < 0
    const prefix = isPast ? '' : 'in '
    const suffix = isPast ? ' ago' : ''
    
    if (diffSec < 60) {
      return 'just now'
    } else if (diffMin < 60) {
      const mins = Math.floor(diffMin)
      return `${prefix}${mins} minute${mins !== 1 ? 's' : ''}${suffix}`
    } else if (diffHour < 24) {
      const hours = Math.floor(diffHour)
      return `${prefix}${hours} hour${hours !== 1 ? 's' : ''}${suffix}`
    } else if (diffDay < 30) {
      const days = Math.floor(diffDay)
      return `${prefix}${days} day${days !== 1 ? 's' : ''}${suffix}`
    } else {
      // For longer periods, just show the formatted date
      return formatDate(dateObj)
    }
  } catch (error) {
    console.error('Error calculating relative time:', error)
    return formatDate(date)
  }
} 