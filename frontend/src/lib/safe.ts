/**
 * Runtime safety utilities for guarding against NaN, null, undefined, and non-array values
 */

/**
 * Ensures a value is an array, returning empty array if not
 */
export function safeArray<T>(value: any): T[] {
  return Array.isArray(value) ? value : []
}

/**
 * Coerces a value to a finite number, returning default if NaN/Infinity/null/undefined
 */
export function toNumber(value: any, defaultValue: number = 0): number {
  if (value === null || value === undefined) {
    return defaultValue
  }

  const num = typeof value === 'number' ? value : parseFloat(value)

  return isFiniteNumber(num) ? num : defaultValue
}

/**
 * Type guard to check if value is a finite number
 */
export function isFiniteNumber(value: any): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

/**
 * Debug logging utility that respects VITE_DEBUG_UI environment variable
 */
export function debugData(data: {
  component: string
  endpoint?: string
  reason: string
  details?: any
}) {
  const debugEnabled = import.meta.env.VITE_DEBUG_UI === 'true' ||
                       import.meta.env.VITE_DEBUG_UI === '1'

  if (debugEnabled) {
    console.debug('[FlexMON Debug]', {
      timestamp: new Date().toISOString(),
      ...data
    })
  }
}
