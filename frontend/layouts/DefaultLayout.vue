<script setup lang="ts">
import { ref, computed } from 'vue';
import Sidebar from '../components/Sidebar.vue';
import GlobalDragDrop from '../components/GlobalDragDrop.vue';
import { useRouter } from 'vue-router';

const router = useRouter();

const emit = defineEmits(['navigate', 'file-dropped']);

// Derive active tab from current route
const activeTab = computed(() => {
  const routeName = router.currentRoute.value.name as string;
  const tabMap: Record<string, string> = {
    'DataManagement': 'data',
    'DeviceImport': 'device',
    'Algorithm': 'algorithm',
    'Reports': 'reports',
    'Settings': 'settings',
  };
  return tabMap[routeName] || 'data';
});

const handleFileUpload = (files: FileList) => {
  emit('file-dropped', files);
};

const handleNavigate = (id: string) => {
    emit('navigate', id);
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
        <slot></slot>
      </main>
    </div>
  </div>
</template>
