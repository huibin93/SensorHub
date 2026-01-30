<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import DefaultLayout from '../layouts/DefaultLayout.vue';

const router = useRouter();
const dataManagementPageRef = ref();

const handleFileDropped = (files: FileList) => {
  // Navigate to data management if not already there
  if (router.currentRoute.value.name !== 'DataManagement') {
    router.push({ name: 'DataManagement' });
  }
  
  // Wait for component to mount, then trigger file select
  setTimeout(() => {
    // Access the exposed method from DataManagementPage
    const routerViewComponent = dataManagementPageRef.value;
    if (routerViewComponent?.handleFileSelect) {
      routerViewComponent.handleFileSelect(files);
    }
  }, 100);
};

const handleNavigate = (id: string) => {
  // Map sidebar navigation IDs to routes
  const routeMap: Record<string, string> = {
    'data': 'DataManagement',
    'device': 'DeviceImport',
    'algorithm': 'Algorithm',
    'reports': 'Reports',
    'settings': 'Settings',
  };
  
  const routeName = routeMap[id];
  if (routeName) {
    router.push({ name: routeName });
  }
};
</script>

<template>
  <DefaultLayout @file-dropped="handleFileDropped" @navigate="handleNavigate">
    <router-view ref="dataManagementPageRef" />
  </DefaultLayout>
</template>
