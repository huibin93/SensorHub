<script setup lang="ts">
import { ref } from 'vue';
import Sidebar from './components/Sidebar.vue';
import ActionArea from './components/ActionArea.vue';
import DataTable from './components/DataTable.vue';
import GlobalDragDrop from './components/GlobalDragDrop.vue';

const actionAreaRef = ref();

const handleFileUpload = (files: FileList) => {
  console.log('Files dropped:', files);
  if (actionAreaRef.value) {
    actionAreaRef.value.handleFileSelect(files);
  }
};
</script>

<template>
  <div class="flex h-screen bg-slate-50 text-slate-800 font-sans overflow-hidden selection:bg-blue-100 selection:text-blue-900 relative">
    <!-- Global Drag Drop Overlay -->
    <GlobalDragDrop @file-dropped="handleFileUpload" />

    <!-- Left: Sidebar -->
    <Sidebar />

    <!-- Right: Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0 bg-slate-50/50 relative">
      
      <main class="flex-1 flex flex-col overflow-hidden px-6 lg:px-10 py-[20px]">
        <div class="w-full flex flex-col gap-4 h-full">
            <!-- Section 2: Action & Stats Area -->
            <ActionArea ref="actionAreaRef" />

            <!-- Section 3: Data Table Area -->
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
      </main>
    </div>
  </div>
</template>
