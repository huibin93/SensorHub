<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue';
import ToastHost from './components/ToastHost.vue';
import { useAuthStore } from './stores/auth';

const authStore = useAuthStore();

onMounted(() => {
  authStore.startHeartbeat();
});

onBeforeUnmount(() => {
  authStore.stopHeartbeat();
});
</script>

<template>
  <ToastHost />
  <RouterView />
</template>
