<template>
  <div class="app-container">
    <!-- Header -->
    <header class="app-header">
      <div>
        <h1>🏠 Floorplan 3D</h1>
        <span class="subtitle">2D to 3D Converter for Japanese Floorplans</span>
      </div>
      <div style="font-size: 0.75rem; color: var(--gray-400);">
        Thesis Project • Akiya 2D→3D Pipeline
      </div>
    </header>
    
    <!-- Main Content -->
    <main class="app-main">
      <!-- Left Sidebar -->
      <div class="sidebar">
        <UploadPanel
          :preview="conversion.filePreview.value"
          :file="conversion.file.value"
          :can-process="conversion.canProcess.value"
          :is-processing="conversion.isProcessing.value"
          :server-ready="conversion.serverReady.value"
          :is-checking-server="conversion.isCheckingServer.value"
          :server-message="conversion.serverMessage.value"
          @file-change="conversion.setFile"
          @process="conversion.processFile"
          @reset="conversion.reset"
        />
        
        <ProgressSteps
          :steps="conversion.steps"
          :step-definitions="conversion.stepDefinitions"
          :error="conversion.error.value"
          :is-complete="conversion.isComplete.value"
          :result="conversion.result.value"
        />
      </div>
      
      <!-- Right Panel - 3D Viewer -->
      <ModelViewer
        :model-url="modelUrl"
        :mtl-url="mtlUrl"
        :is-processing="conversion.isProcessing.value"
        :result="conversion.result.value"
      />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import UploadPanel from './components/UploadPanel.vue'
import ProgressSteps from './components/ProgressSteps.vue'
import ModelViewer from './components/ModelViewer.vue'
import { useConversion } from './composables/useConversion.js'

const conversion = useConversion()

// Computed URLs for the viewer
const modelUrl = computed(() => conversion.result.value?.obj_url || null)
const mtlUrl = computed(() => conversion.result.value?.mtl_url || null)

// Warmup model on app load for faster first conversion
onMounted(() => {
  conversion.checkHealth()
})
</script>
