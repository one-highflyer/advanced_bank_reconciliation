import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import type { MatchedTransaction } from './types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format currency value
 */
export function formatCurrency(value: number, currency: string = 'USD'): string {
  if (!value && value !== 0) return '';
  
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Check if a transaction is selected from a list of selected transactions
 */
export function isTransactionSelected(
  selectedTransactions: MatchedTransaction[],
  doctype: string,
  docname: string
): boolean {
  return selectedTransactions.some(t => t.doctype === doctype && t.docname === docname);
}
