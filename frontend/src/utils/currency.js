import { formatCurrency as formatCurrencyUtil } from './formatters.js'

/**
 * Format currency value with proper locale and currency code
 * @param {number} amount - Amount to format
 * @param {string} currency - Currency code
 * @param {string} locale - Locale for formatting
 * @returns {string} Formatted currency string
 */
export function formatCurrency(amount, currency = 'USD', locale = 'en-US') {
  return formatCurrencyUtil(amount, currency, locale)
}

/**
 * Round a number to specified decimal places
 * @param {number} value - Number to round
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {number} Rounded number
 */
export function round(value, decimals = 2) {
  if (value === null || value === undefined || isNaN(value)) return 0
  
  const factor = Math.pow(10, decimals)
  return Math.round(value * factor) / factor
}

/**
 * Calculate percentage of a value
 * @param {number} value - Value to calculate percentage of
 * @param {number} total - Total value
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {number} Percentage value
 */
export function calculatePercentage(value, total, decimals = 2) {
  if (total === 0) return 0
  return round((value / total) * 100, decimals)
}

/**
 * Add multiple currency values
 * @param {...number} values - Values to add
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {number} Sum of values
 */
export function add(...values) {
  const sum = values.reduce((acc, val) => acc + (val || 0), 0)
  return round(sum, 2)
}

/**
 * Subtract currency values
 * @param {number} a - First value
 * @param {number} b - Second value
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {number} Difference
 */
export function subtract(a, b, decimals = 2) {
  return round((a || 0) - (b || 0), decimals)
}

/**
 * Multiply currency values
 * @param {number} a - First value
 * @param {number} b - Second value
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {number} Product
 */
export function multiply(a, b, decimals = 2) {
  return round((a || 0) * (b || 0), decimals)
}

/**
 * Divide currency values
 * @param {number} a - First value
 * @param {number} b - Second value
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {number} Quotient
 */
export function divide(a, b, decimals = 2) {
  if (b === 0) return 0
  return round((a || 0) / b, decimals)
}

/**
 * Check if two currency values are equal (within tolerance)
 * @param {number} a - First value
 * @param {number} b - Second value
 * @param {number} tolerance - Tolerance for comparison (default: 0.01)
 * @returns {boolean} True if values are equal within tolerance
 */
export function isEqual(a, b, tolerance = 0.01) {
  return Math.abs((a || 0) - (b || 0)) < tolerance
}

/**
 * Get the absolute value of a currency amount
 * @param {number} value - Value to get absolute value of
 * @returns {number} Absolute value
 */
export function abs(value) {
  return Math.abs(value || 0)
}

/**
 * Get the maximum of multiple currency values
 * @param {...number} values - Values to compare
 * @returns {number} Maximum value
 */
export function max(...values) {
  return Math.max(...values.filter(v => v !== null && v !== undefined))
}

/**
 * Get the minimum of multiple currency values
 * @param {...number} values - Values to compare
 * @returns {number} Minimum value
 */
export function min(...values) {
  return Math.min(...values.filter(v => v !== null && v !== undefined))
}

/**
 * Format a range of currency values
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @param {string} currency - Currency code
 * @param {string} locale - Locale for formatting
 * @returns {string} Formatted range string
 */
export function formatRange(min, max, currency = 'USD', locale = 'en-US') {
  if (min === max) {
    return formatCurrency(min, currency, locale)
  }
  return `${formatCurrency(min, currency, locale)} - ${formatCurrency(max, currency, locale)}`
}

/**
 * Parse a currency string to a number
 * @param {string} value - Currency string to parse
 * @param {string} locale - Locale for parsing
 * @returns {number} Parsed number
 */
export function parseCurrency(value, locale = 'en-US') {
  if (!value || typeof value !== 'string') return 0
  
  // Remove currency symbols and spaces
  const cleanValue = value.replace(/[^\d.,-]/g, '')
  
  // Handle different decimal separators
  const parts = cleanValue.split(/[,.]/)
  if (parts.length === 1) {
    return parseFloat(parts[0]) || 0
  }
  
  // Assume last part is decimal
  const decimalPart = parts.pop()
  const integerPart = parts.join('')
  
  return parseFloat(`${integerPart}.${decimalPart}`) || 0
} 