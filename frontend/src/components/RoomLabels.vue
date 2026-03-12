<template>
  <div v-if="labelsVisible">
    <div v-for="room in rooms" :key="room.centroid.join('-')" class="room-label" :style="labelStyle(room)">
      {{ room.class_name }} ({{ Math.round(room.mean_confidence * 100) }}%)
    </div>
  </div>
</template>

<script setup>
import { computed, toRefs } from 'vue'
const props = defineProps({
  rooms: Array, // per_room_confidence array
  labelsVisible: Boolean,
  imageToWorld: Function, // function to map [x, y] to [x, y, z] in 3D
  projectToScreen: Function // function to map 3D to screen coords
})

// Compute style for each label (absolute positioning)
function labelStyle(room) {
  if (!props.projectToScreen) return {}
  const world = props.imageToWorld(room.centroid)
  const screen = props.projectToScreen(world)
  return {
    position: 'absolute',
    left: screen.x + 'px',
    top: screen.y + 'px',
    pointerEvents: 'none',
    background: 'rgba(0,0,0,0.7)',
    color: '#fff',
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '0.85em',
    transform: 'translate(-50%, -100%)',
    whiteSpace: 'nowrap',
    zIndex: 10
  }
}
</script>

<style scoped>
.room-label {
  font-family: inherit;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
</style>
