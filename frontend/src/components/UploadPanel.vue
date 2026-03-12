<template>
  <div class="panel">
    <div class="panel-header">📁 Upload Floorplan</div>
    <div class="panel-content">
      <!-- Upload Area -->
      <div
        class="upload-area"
        :class="{ 'drag-over': isDragging, 'has-file': hasFile }"
        @click="triggerFileInput"
        @drop.prevent="handleDrop"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
      >
        <input
          ref="fileInput"
          type="file"
          accept="image/png,image/jpeg"
          hidden
          @change="handleFileSelect"
        />
        
        <!-- Preview or Placeholder -->
        <template v-if="preview">
          <img :src="preview" alt="Preview" class="preview-image" />
          <div class="upload-text">{{ fileName }}</div>
        </template>
        <template v-else>
          <div class="upload-icon">📤</div>
          <div class="upload-text">
            Drop your floorplan here<br>or click to browse
          </div>
          <div class="upload-hint">PNG or JPG, max 10MB</div>
        </template>
      </div>
      
      <!-- Actions -->
      <div style="margin-top: 1rem; display: flex; flex-direction: column; gap: 0.5rem;">
        <button
          class="btn btn-primary"
          :disabled="!canProcess || isProcessing"
          @click="$emit('process')"
        >
          <span v-if="isProcessing" class="spinner"></span>
          <span v-else>🚀</span>
          {{ isProcessing ? 'Processing...' : 'Convert to 3D' }}
        </button>
        
        <button
          v-if="hasFile"
          class="btn btn-secondary"
          :disabled="isProcessing"
          @click="$emit('reset')"
        >
          ✕ Clear
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  preview: String,
  file: Object,
  canProcess: Boolean,
  isProcessing: Boolean,
})

const emit = defineEmits(['file-change', 'process', 'reset'])

const fileInput = ref(null)
const isDragging = ref(false)

const hasFile = computed(() => !!props.file)
const fileName = computed(() => props.file?.name || '')

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileSelect(event) {
  const file = event.target.files?.[0]
  if (file) {
    emit('file-change', file)
  }
}

function handleDrop(event) {
  isDragging.value = false
  const file = event.dataTransfer.files?.[0]
  if (file && (file.type === 'image/png' || file.type === 'image/jpeg')) {
    emit('file-change', file)
  }
}
</script>
