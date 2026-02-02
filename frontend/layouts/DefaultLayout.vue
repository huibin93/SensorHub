<script setup lang="ts">
import { ref, computed, provide } from 'vue';
import Sidebar from '../components/Sidebar.vue';
import GlobalDragDrop from '../components/GlobalDragDrop.vue';
import { useRouter } from 'vue-router';

const router = useRouter();

const emit = defineEmits(['navigate']);

// Derive active tab from current route
const activeTab = computed(() => {
  const routeName = router.currentRoute.value.name as string;
  const tabMap: Record<string, string> = {
    'DataManagement': 'data',
    'DeviceImport': 'device',
    'Algorithm': 'algorithm',
    'Reports': 'reports',
    'Settings': 'settings',
    'SerialTool': 'serial',
    'LogAnalysis': 'logs',
    'AdminUser': 'users',
  };
  return tabMap[routeName] || 'data';
});

// 创建可供子组件调用的函数
const fileDropHandler = ref<((files: FileList) => void) | null>(null);

// 注册子组件的文件处理器
const registerFileDropHandler = (handler: (files: FileList) => void) => {
  fileDropHandler.value = handler;
};

// 提供给子组件使用
provide('registerFileDropHandler', registerFileDropHandler);

const handleFileUpload = (files: FileList) => {
  // 调用注册的处理器
  if (fileDropHandler.value) {
    fileDropHandler.value(files);
  }
};

const handleNavigate = (id: string) => {
    emit('navigate', id);
};
</script>

<template>
  <div class="flex h-screen bg-slate-50 text-slate-800 font-sans overflow-hidden selection:bg-blue-100 selection:text-blue-900 relative">
    <!-- Global Drag Drop Overlay - 只在 Data Management 页面启用 -->
    <GlobalDragDrop 
      :enabled="activeTab === 'data'" 
      @file-dropped="handleFileUpload" 
    />

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
