<script setup lang="ts">
import { ref } from 'vue';
import ActionArea from '../components/ActionArea.vue';
import DataTable from '../components/DataTable.vue';

const actionAreaRef = ref();

// Expose method for external file upload trigger (from drag-drop)
defineExpose({
  handleFileSelect: (files: FileList) => {
    if (actionAreaRef.value) {
      actionAreaRef.value.handleFileSelect(files);
    }
  }
});
</script>

<template>
  <div class="w-full flex flex-col gap-4 h-full animate-in fade-in slide-in-from-bottom-2 duration-300">
    <!-- Section 1: Action & Stats Area -->
    <ActionArea ref="actionAreaRef" />

    <!-- Section 2: Data Table Area -->
    <section class="flex-1 flex flex-col gap-4 min-h-0 overflow-hidden">
      <div class="flex items-center justify-between px-1 shrink-0">
        <h2 class="text-lg font-bold text-slate-700 tracking-tight">Data Files</h2>
        <div class="flex gap-2">
          <!-- Optional Top Actions -->
        </div>
      </div>
      <div class="flex-1 min-h-0 flex flex-col">
        <DataTable />
      </div>
    </section>
  </div>
</template>
