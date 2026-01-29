<script setup lang="ts">
import { ref } from 'vue';
import Sidebar from './components/Sidebar.vue';
import ActionArea from './components/ActionArea.vue';
import DataTable from './components/DataTable.vue';
import GlobalDragDrop from './components/GlobalDragDrop.vue';
import DeviceImport from './components/DeviceImport.vue';

const actionAreaRef = ref();
const activeTab = ref('data');

const handleFileUpload = (files: FileList) => {
  console.log('Files dropped:', files);
  if (activeTab.value !== 'data') {
      activeTab.value = 'data';
      // Wait for next tick to ensure ref is bound? 
      // Simplified: Just prompt user or switch tab. 
      // user will see tab switch and then can drop again or we manually trigger.
      // For now, simple check:
  }
  
  // We need to wait for component mount if we just switched.
  setTimeout(() => {
      if (actionAreaRef.value) {
        actionAreaRef.value.handleFileSelect(files);
      }
  }, 100);
};

const handleNavigate = (id: string) => {
    activeTab.value = id;
};
</script>

<template>
  <div class="flex h-screen bg-slate-50 text-slate-800 font-sans overflow-hidden selection:bg-blue-100 selection:text-blue-900 relative">
    <!-- Global Drag Drop Overlay -->
    <GlobalDragDrop @file-dropped="handleFileUpload" />

    <!-- Left: Sidebar -->
    <Sidebar :activeId="activeTab" @navigate="handleNavigate" />

    <!-- Right: Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0 bg-slate-50/50 relative">
      
      <main class="flex-1 flex flex-col overflow-hidden px-6 lg:px-10 py-[20px]">
        <!-- DATA MANAGEMENT VIEW -->
        <div v-if="activeTab === 'data'" class="w-full flex flex-col gap-4 h-full animate-in fade-in slide-in-from-bottom-2 duration-300">
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

        <!-- DEVICE IMPORT VIEW -->
        <div v-else-if="activeTab === 'device'" class="w-full h-full animate-in fade-in slide-in-from-bottom-2 duration-300">
            <DeviceImport />
        </div>

        <!-- PLACEHOLDER VIEW -->
        <div v-else class="w-full h-full flex flex-col items-center justify-center text-slate-400 animate-in fade-in">
             <div class="text-xl font-bold">Work in Progress</div>
             <div class="text-sm mt-2">The {{ activeTab }} module is coming soon.</div>
        </div>

      </main>
    </div>
  </div>
</template>
