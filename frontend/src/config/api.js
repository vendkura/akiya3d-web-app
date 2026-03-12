/**
 * API configuration for different environments
 */

// Get API base URL from environment variable or default to localhost for development
const getApiBaseUrl = () => {
  // In production (Vercel), use environment variable
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  
  // Development fallback
  return 'http://localhost:8000'
}

export const API_BASE_URL = getApiBaseUrl()
export const API_ENDPOINTS = {
  convert: `${API_BASE_URL}/api/v1/convert`,
  warmup: `${API_BASE_URL}/api/v1/warmup`,
  health: `${API_BASE_URL}/health`,
}

console.log('API Base URL:', API_BASE_URL)