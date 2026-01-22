<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { UploadCloud } from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'file-dropped', files: FileList): void
}>();

const isDragging = ref(false);
const dragCounter = ref(0);

const handleDragEnter = (e: DragEvent) => {
  e.preventDefault();
  dragCounter.value++;
  if (e.dataTransfer) {
     isDragging.value = true;
  }
};

const handleDragLeave = (e: DragEvent) => {
  e.preventDefault();
  dragCounter.value--;
  if (dragCounter.value <= 0) {
    isDragging.value = false;
    dragCounter.value = 0;
  }
};

const handleDragOver = (e: DragEvent) => {
  e.preventDefault(); // Necessary to allow dropping
};

const handleDrop = (e: DragEvent) => {
  e.preventDefault();
  isDragging.value = false;
  dragCounter.value = 0;
  
  if (e.dataTransfer && e.dataTransfer.files.length > 0) {
    emit('file-dropped', e.dataTransfer.files);
  }
};

onMounted(() => {
  window.addEventListener('dragenter', handleDragEnter);
  window.addEventListener('dragleave', handleDragLeave);
  window.addEventListener('dragover', handleDragOver);
  window.addEventListener('drop', handleDrop);
});

onUnmounted(() => {
  window.removeEventListener('dragenter', handleDragEnter);
  window.removeEventListener('dragleave', handleDragLeave);
  window.removeEventListener('dragover', handleDragOver);
  window.removeEventListener('drop', handleDrop);
});
</script>

<template>
  <Transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="opacity-0 scale-95"
    enter-to-class="opacity-100 scale-100"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="opacity-100 scale-100"
    leave-to-class="opacity-0 scale-95"
  >
    <div 
      v-show="isDragging"
      class="fixed inset-0 z-50 flex items-center justify-center bg-blue-50/60 backdrop-blur-sm"
    >
      <!-- Dashed Border Box -->
      <div class="w-[80%] h-[80%] border-4 border-dashed border-blue-400 rounded-3xl flex flex-col items-center justify-center bg-white/40 shadow-2xl pointer-events-none">
          <div class="p-6 bg-blue-500 text-white rounded-full mb-6 shadow-lg shadow-blue-500/30 animate-bounce">
              <UploadCloud :size="48" />
          </div>
          <h2 class="text-3xl font-bold text-slate-800 mb-2">Drop files to upload</h2>
          <p class="text-lg text-slate-600">Release your mouse to start uploading</p>
      </div>
    </div>
  </Transition>
</template>
