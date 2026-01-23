<script setup lang="ts">
import Sidebar from './components/Sidebar.vue';
import ActionArea from './components/ActionArea.vue';
import DataTable from './components/DataTable.vue';
import GlobalDragDrop from './components/GlobalDragDrop.vue';

const handleFileUpload = (files: FileList) => {
  console.log('Files dropped:', files);
  const fileNames = Array.from(files).map(f => f.name).join(', ');
  alert(`Caught ${files.length} file(s):\n${fileNames}`);
  // In real app, you would pass these to your upload logic
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
        <div class="max-w-[1600px] mx-auto w-full flex flex-col gap-4 h-full">
            <!-- Section 2: Action & Stats Area -->
            <ActionArea />

            <!-- Section 3: Data Table Area -->
            <section class="flex-1 flex flex-col gap-4 min-h-0 overflow-hidden">
                <div class="flex items-center justify-between px-1 shrink-0">
                <h2 class="text-lg font-bold text-slate-700 tracking-tight">Recent Data Files</h2>
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
