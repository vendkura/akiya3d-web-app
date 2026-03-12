import { ref, reactive, computed } from 'vue'
import { API_ENDPOINTS } from '../config/api.js'

/**
 * Composable for handling floorplan conversion API with SSE progress
 * Updated for Pipeline v5 (Dollhouse Style)
 */
export function useConversion() {
  // State
  const file = ref(null)
  const filePreview = ref(null)
  const isProcessing = ref(false)
  const isComplete = ref(false)
  const error = ref(null)
  const result = ref(null)
  
  // Steps state - Pipeline v5 steps
  const steps = reactive({
    segmentation: { status: 'pending', progress: 0, message: '', data: null },
    postprocess: { status: 'pending', progress: 0, message: '', data: null },
    fitting: { status: 'pending', progress: 0, message: '', data: null },
    extrusion: { status: 'pending', progress: 0, message: '', data: null },
    export: { status: 'pending', progress: 0, message: '', data: null },
  })
  
  // Step definitions for display - Pipeline v5
  const stepDefinitions = [
    { key: 'segmentation', label: 'FPN Segmentation', icon: '🎨' },
    { key: 'postprocess', label: 'Post-Processing', icon: '🧹' },
    { key: 'fitting', label: 'Rectangular Fitting', icon: '📐' },
    { key: 'extrusion', label: 'Wall Extrusion', icon: '🏗️' },
    { key: 'export', label: 'Export Files', icon: '📦' },
  ]
  
  // Computed
  const canProcess = computed(() => file.value && !isProcessing.value)
  
  const currentStep = computed(() => {
    for (const def of stepDefinitions) {
      if (steps[def.key].status === 'running') return def.key
    }
    return null
  })
  
  // Methods
  function setFile(newFile) {
    file.value = newFile
    error.value = null
    isComplete.value = false
    result.value = null
    
    // Reset steps
    for (const key of Object.keys(steps)) {
      steps[key] = { status: 'pending', progress: 0, message: '', data: null }
    }
    
    // Create preview URL
    if (newFile) {
      filePreview.value = URL.createObjectURL(newFile)
    } else {
      filePreview.value = null
    }
  }
  
  function reset() {
    setFile(null)
  }
  
  async function processFile() {
    if (!file.value) return
    
    isProcessing.value = true
    error.value = null
    isComplete.value = false
    result.value = null
    
    // Reset steps to pending
    for (const key of Object.keys(steps)) {
      steps[key] = { status: 'pending', progress: 0, message: '', data: null }
    }
    
    try {
      // Create form data
      const formData = new FormData()
      formData.append('file', file.value)
      
      // Make SSE request
      const response = await fetch(API_ENDPOINTS.convert, {
        method: 'POST',
        body: formData,
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      // Read SSE stream
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      
      console.log('Starting SSE stream reading...')
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          console.log('SSE stream ended')
          break
        }
        
        const chunk = decoder.decode(value, { stream: true })
        buffer += chunk
        console.log('Received chunk:', chunk.substring(0, 100))
        
        // Process complete SSE messages (split by double newline)
        const messages = buffer.split('\n\n')
        buffer = messages.pop() || '' // Keep incomplete message in buffer
        
        console.log('Found', messages.length, 'complete messages')
        
        for (const message of messages) {
          // Each message can have multiple lines, find the data line
          const lines = message.split('\n')
          for (const line of lines) {
            if (line.startsWith('data:')) {
              // Handle both 'data: {...}' and 'data:{...}'
              const jsonStr = line.startsWith('data: ') ? line.slice(6) : line.slice(5)
              if (jsonStr.trim()) {
                try {
                  const data = JSON.parse(jsonStr)
                  handleSSEMessage(data)
                } catch (e) {
                  console.warn('Failed to parse SSE message:', e.message, jsonStr.substring(0, 100))
                }
              }
            }
          }
        }
      }
      
      // Process any remaining buffer
      if (buffer.trim()) {
        console.log('Processing remaining buffer:', buffer.substring(0, 100))
        const lines = buffer.split('\n')
        for (const line of lines) {
          if (line.startsWith('data:')) {
            const jsonStr = line.startsWith('data: ') ? line.slice(6) : line.slice(5)
            if (jsonStr.trim()) {
              try {
                const data = JSON.parse(jsonStr)
                handleSSEMessage(data)
              } catch (e) {
                console.warn('Failed to parse remaining SSE:', e.message)
              }
            }
          }
        }
      }
      
    } catch (e) {
      console.error('Conversion error:', e)
      error.value = e.message
    } finally {
      isProcessing.value = false
    }
  }
  
  function handleSSEMessage(data) {
    console.log('SSE message received:', data)
    
    // Check if it's a step update or final result
    if (data.name && data.status) {
      // Step update
      const stepKey = data.name
      if (steps[stepKey]) {
        steps[stepKey] = {
          status: data.status,
          progress: data.progress || 0,
          message: data.message || '',
          data: data.data || null,
        }
        console.log('Step updated:', stepKey, steps[stepKey].status)
      }
    } else if ('success' in data) {
      // Final result
      console.log('Final result received:', data.success, 'obj_url:', data.obj_url)
      if (data.success) {
        isComplete.value = true
        result.value = data
        console.log('Result set! obj_url:', result.value?.obj_url)
      } else {
        error.value = data.error || 'Unknown error'
      }
    }
  }
  
  // Warmup the model on load
  async function warmup() {
    try {
      await fetch(API_ENDPOINTS.warmup, { method: 'POST' })
    } catch (e) {
      console.warn('Warmup failed:', e)
    }
  }
  
  return {
    // State
    file,
    filePreview,
    isProcessing,
    isComplete,
    error,
    result,
    steps,
    stepDefinitions,
    
    // Computed
    canProcess,
    currentStep,
    
    // Methods
    setFile,
    reset,
    processFile,
    warmup,
  }
}
