<template>
  <div class="panel viewer-panel">
    <div class="panel-header">🏠 3D Preview</div>
    
    <!-- Debug info (remove later) -->
    <div v-if="modelUrl" style="background: #333; padding: 8px; font-size: 11px; color: #0f0;">
      <div>URL: {{ modelUrl?.substring(0, 50) }}...</div>
      <div>Loading: {{ isLoadingModel }} | Error: {{ loadError || 'none' }}</div>
      <div>Scene: {{ !!scene }} | Renderer: {{ !!renderer }} | Model: {{ !!loadedModel }}</div>
    </div>
    
    <div class="viewer-container" ref="containerRef">
      <!-- Empty State -->
      <div v-if="!modelUrl && !isProcessing" class="empty-state">
        <div class="empty-state-icon">🏗️</div>
        <div class="empty-state-text">
          Upload a floorplan to see<br>the 3D model here
        </div>
      </div>
      
      <!-- Loading State -->
      <div v-else-if="isProcessing && !modelUrl" class="empty-state">
        <div class="empty-state-icon">⏳</div>
        <div class="empty-state-text">
          Generating 3D model...
        </div>
      </div>
      
      <!-- Loading Model State -->
      <div v-else-if="modelUrl && isLoadingModel" class="empty-state">
        <div class="empty-state-icon">📦</div>
        <div class="empty-state-text">
          Loading 3D model...
        </div>
      </div>
      
      <!-- Error State -->
      <div v-if="loadError" class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-text" style="color: #ef4444;">
          Failed to load model<br>
          <small>{{ loadError }}</small>
        </div>
      </div>
      
      <!-- 3D Viewer Canvas - always rendered when we have a URL -->
      <canvas 
        ref="canvasRef" 
        v-show="modelUrl"
        :style="{ opacity: isLoadingModel ? 0.3 : 1 }"
        style="width: 100%; height: 100%; display: block;"
      ></canvas>
      
      <!-- Loading overlay -->
      <div v-if="modelUrl && isLoadingModel" class="loading-overlay">
        <div class="empty-state-icon">📦</div>
        <div class="empty-state-text">Loading 3D model...</div>
      </div>
      
      <RoomLabels
        v-if="roomLabels.length && showLabels"
        :rooms="roomLabels"
        :labelsVisible="showLabels"
        :imageToWorld="imageToWorld"
        :projectToScreen="projectToScreen"
      />
    </div>
    
    <!-- Controls -->
    <div v-if="modelUrl && !loadError" class="viewer-controls">
      <button class="btn btn-secondary" @click="resetCamera">
        🎯 Reset View
      </button>
      <button class="btn btn-secondary" @click="toggleWireframe">
        {{ wireframe ? '🔲 Solid' : '📐 Wireframe' }}
      </button>
      <button class="btn btn-secondary" @click="showLabels = !showLabels">
        {{ showLabels ? 'Hide Labels' : 'Show Labels' }}
      </button>
      <a :href="modelUrl" download class="btn btn-primary" style="text-decoration: none;">
        ⬇️ Download OBJ
      </a>
    </div>
  </div>
</template>

<script setup>
import RoomLabels from './RoomLabels.vue'
import { computed, ref, watch, onMounted, onUnmounted, shallowRef } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js'

const props = defineProps({
  modelUrl: String,
  mtlUrl: String,
  isProcessing: Boolean,
})

// Refs
const canvasRef = ref(null)
const containerRef = ref(null)
const wireframe = ref(false)
const isLoadingModel = ref(false)
const loadError = ref(null)

// Three.js objects - using shallowRef so template can access them for debugging
const renderer = shallowRef(null)
const scene = shallowRef(null)
const loadedModel = shallowRef(null)
let camera = null
let controls = null
let animationId = null

// Room label state
const roomLabels = ref([])
const showLabels = ref(false)

// Initialize Three.js scene
function initScene() {
  if (!canvasRef.value || !containerRef.value) {
    console.warn('Canvas or container not ready')
    return false
  }
  
  if (renderer.value) {
    console.log('Scene already initialized')
    return true
  }
  
  const container = containerRef.value
  const canvas = canvasRef.value
  
  // Get dimensions - use minimum if hidden
  const width = container.clientWidth || 800
  const height = container.clientHeight || 600
  
  console.log('Initializing scene with dimensions:', width, height)
  
  // Scene
  scene.value = new THREE.Scene()
  scene.value.background = new THREE.Color(0x1a1a2e)
  
  // Camera
  camera = new THREE.PerspectiveCamera(
    60,
    width / height,
    0.1,
    1000
  )
  camera.position.set(15, 15, 15)
  
  // Renderer
  renderer.value = new THREE.WebGLRenderer({ 
    canvas, 
    antialias: true 
  })
  renderer.value.setSize(width, height)
  renderer.value.setPixelRatio(window.devicePixelRatio)
  renderer.value.shadowMap.enabled = true
  
  // Controls
  controls = new OrbitControls(camera, renderer.value.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  
  // Lights
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
  scene.value.add(ambientLight)
  
  const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.8)
  directionalLight1.position.set(10, 20, 10)
  directionalLight1.castShadow = true
  scene.value.add(directionalLight1)
  
  const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.4)
  directionalLight2.position.set(-10, 10, -10)
  scene.value.add(directionalLight2)
  
  // Animation loop
  function animate() {
    animationId = requestAnimationFrame(animate)
    controls.update()
    renderer.value.render(scene.value, camera)
  }
  animate()
  
  // Handle resize
  window.addEventListener('resize', handleResize)
  
  console.log('Three.js scene initialized')
  return true
}

function handleResize() {
  if (!containerRef.value || !camera || !renderer.value) return
  
  const container = containerRef.value
  camera.aspect = container.clientWidth / container.clientHeight
  camera.updateProjectionMatrix()
  renderer.value.setSize(container.clientWidth, container.clientHeight)
}

// Load OBJ model
async function loadModel(objUrl, mtlUrl) {
  if (!scene.value) {
    console.warn('Scene not initialized, initializing now...')
    initScene()
    // Wait a bit for scene to be ready
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  
  console.log('Loading model:', objUrl)
  console.log('MTL URL:', mtlUrl)
  
  isLoadingModel.value = true
  loadError.value = null
  
  // Remove old model
  if (loadedModel.value) {
    scene.value.remove(loadedModel.value)
    loadedModel.value = null
  }
  
  try {
    // Load MTL first if available
    let materials = null
    if (mtlUrl) {
      try {
        const mtlLoader = new MTLLoader()
        materials = await new Promise((resolve, reject) => {
          mtlLoader.load(
            mtlUrl,
            (mtl) => {
              mtl.preload()
              console.log('MTL loaded successfully')
              resolve(mtl)
            },
            undefined,
            (error) => {
              console.warn('MTL load failed:', error)
              resolve(null)
            }
          )
        })
      } catch (e) {
        console.warn('MTL not available:', e)
      }
    }
    
    // Load OBJ
    const objLoader = new OBJLoader()
    if (materials) {
      objLoader.setMaterials(materials)
    }
    
    const obj = await new Promise((resolve, reject) => {
      objLoader.load(
        objUrl,
        (object) => {
          console.log('OBJ loaded successfully')
          resolve(object)
        },
        (progress) => {
          if (progress.total > 0) {
            console.log('Loading progress:', Math.round(progress.loaded / progress.total * 100) + '%')
          }
        },
        (error) => {
          console.error('OBJ load error:', error)
          reject(new Error('Failed to load OBJ file'))
        }
      )
    })
    
    // Apply default material if needed
    obj.traverse((child) => {
      if (child.isMesh) {
        if (!child.material || !materials) {
          child.material = new THREE.MeshStandardMaterial({
            color: 0x8888ff,
            roughness: 0.7,
            metalness: 0.1,
            side: THREE.DoubleSide,
            wireframe: wireframe.value
          })
        }
        child.castShadow = true
        child.receiveShadow = true
      }
    })
    
    // Center and scale model
    const box = new THREE.Box3().setFromObject(obj)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    
    console.log('Model size:', size)
    console.log('Model center:', center)
    console.log('Model bounds Y: min=', box.min.y, 'max=', box.max.y)
    
    // Center in X and Z, but place bottom on the grid (Y=0)
    obj.position.x -= center.x
    obj.position.z -= center.z
    obj.position.y -= box.min.y  // Move bottom to Y=0
    
    // Scale to fit view if too large
    const maxDim = Math.max(size.x, size.y, size.z)
    if (maxDim > 20) {
      const scale = 20 / maxDim
      obj.scale.setScalar(scale)
      console.log('Scaled model by:', scale)
    }
    
    scene.value.add(obj)
    loadedModel.value = obj
    
    // Reset camera to view model
    resetCamera()
    
    isLoadingModel.value = false
    console.log('Model loaded and added to scene!')
    
  } catch (error) {
    console.error('Model loading failed:', error)
    loadError.value = error.message
    isLoadingModel.value = false
  }
}

function resetCamera() {
  if (!camera || !controls) return
  
  camera.position.set(15, 15, 15)
  camera.lookAt(0, 0, 0)
  controls.target.set(0, 0, 0)
  controls.update()
}

function toggleWireframe() {
  wireframe.value = !wireframe.value
  
  if (loadedModel.value) {
    loadedModel.value.traverse((child) => {
      if (child.isMesh && child.material) {
        child.material.wireframe = wireframe.value
      }
    })
  }
}

// Map image centroid to 3D world coordinates (approximate)
function imageToWorld([imgX, imgY]) {
  // Assume OBJ is centered and scaled as in loadModel()
  // Map image (0,0) top-left to model's bounding box
  if (!loadedModel.value) return [0, 0, 0]
  const box = new THREE.Box3().setFromObject(loadedModel.value)
  const size = box.getSize(new THREE.Vector3())
  const min = box.min
  // Assume image coords are in [0, W] x [0, H], map to model X/Z
  // You may need to adjust this mapping based on your pipeline
  // For now, map X to X, Y to -Z (since Three.js Y is up)
  // If you know the image size, you can scale accordingly
  // Here, we just center in the model's bounding box
  const x = min.x + (imgX / 512) * size.x // TODO: replace 512 with real image width
  const z = min.z + (imgY / 512) * size.z // TODO: replace 512 with real image height
  return [x, 0.1, z] // Slightly above floor
}

// Project 3D world to screen coordinates
function projectToScreen([x, y, z]) {
  if (!camera || !renderer.value) return { x: 0, y: 0 }
  const width = renderer.value.domElement.width
  const height = renderer.value.domElement.height
  const vector = new THREE.Vector3(x, y, z)
  vector.project(camera)
  return {
    x: (vector.x + 1) / 2 * width,
    y: (-vector.y + 1) / 2 * height
  }
}

// Watch for new per_room_confidence data
watch(() => props.result, (newResult) => {
  if (newResult && newResult.per_room_confidence) {
    roomLabels.value = newResult.per_room_confidence
  } else {
    roomLabels.value = []
  }
})

// Watch for model URL changes
watch(() => props.modelUrl, async (newUrl) => {
  if (newUrl) {
    console.log('Model URL changed:', newUrl)
    // Wait for next tick to ensure DOM is updated
    await new Promise(resolve => setTimeout(resolve, 50))
    loadModel(newUrl, props.mtlUrl)
  }
})

// Lifecycle
onMounted(() => {
  console.log('ModelViewer mounted')
  initScene()
  
  // If we already have a model URL, load it
  if (props.modelUrl) {
    console.log('Initial model URL:', props.modelUrl)
    setTimeout(() => loadModel(props.modelUrl, props.mtlUrl), 100)
  }
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  window.removeEventListener('resize', handleResize)
  if (renderer.value) {
    renderer.value.dispose()
  }
})
</script>

<style scoped>
.viewer-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.viewer-container {
  flex: 1;
  position: relative;
  min-height: 400px;
  background: #1a1a2e;
  border-radius: var(--radius);
  overflow: hidden;
}

.empty-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(26, 26, 46, 0.8);
  z-index: 10;
}
</style>
