<template>
  <div class="panel">
    <div class="panel-header">⚡ Processing Steps</div>
    <div class="panel-content">
      <div class="steps-container">
        <div
          v-for="(step, index) in stepDefinitions"
          :key="step.key"
          class="step"
          :class="{
            active: steps[step.key].status === 'running',
            completed: steps[step.key].status === 'completed',
            error: steps[step.key].status === 'error',
          }"
        >
          <!-- Step Icon -->
          <div class="step-icon">
            <template v-if="steps[step.key].status === 'running'">
              <span class="spinner"></span>
            </template>
            <template v-else-if="steps[step.key].status === 'completed'">
              ✓
            </template>
            <template v-else-if="steps[step.key].status === 'error'">
              ✕
            </template>
            <template v-else>
              {{ index + 1 }}
            </template>
          </div>
          
          <!-- Step Content -->
          <div class="step-content">
            <div class="step-label">{{ step.icon }} {{ step.label }}</div>
            <div v-if="steps[step.key].message" class="step-message">
              {{ steps[step.key].message }}
            </div>
            
            <!-- Preview image for segmentation/boundary steps -->
            <div
              v-if="steps[step.key].data?.preview"
              class="step-preview"
            >
              <img :src="steps[step.key].data.preview" :alt="step.label + ' preview'" />
            </div>
          </div>
        </div>
      </div>
      
      <!-- Error Message -->
      <div v-if="error" style="margin-top: 1rem; padding: 0.75rem; background: rgba(239,68,68,0.1); border-radius: var(--radius); color: var(--error); font-size: 0.875rem;">
        ⚠️ {{ error }}
      </div>
      
      <!-- Results -->
      <div v-if="isComplete && result" style="margin-top: 1rem;">
        <div style="font-weight: 600; font-size: 0.875rem; margin-bottom: 0.5rem; color: var(--success);">
          ✅ Conversion Complete!
        </div>
        <div class="results-grid">
          <a :href="result.obj_url" class="result-item" download>
            <span class="result-icon">📦</span>
            <span>model.obj</span>
          </a>
          <a :href="result.mtl_url" class="result-item" download>
            <span class="result-icon">🎨</span>
            <span>model.mtl</span>
          </a>
          <a :href="result.mask_url" class="result-item" download>
            <span class="result-icon">🖼️</span>
            <span>mask.png</span>
          </a>
          <a :href="result.boundaries_url" class="result-item" download>
            <span class="result-icon">📋</span>
            <span>boundaries.json</span>
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  steps: Object,
  stepDefinitions: Array,
  error: String,
  isComplete: Boolean,
  result: Object,
})
</script>

<style scoped>
.results-grid a {
  text-decoration: none;
  color: inherit;
  cursor: pointer;
}

.results-grid a:hover {
  background: var(--gray-100);
}
</style>
