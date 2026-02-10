<script setup lang="ts">
import { useToast } from '../composables/useToast';

const { toasts } = useToast();
</script>

<template>
  <div class="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
    <transition-group name="toast" tag="div">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto flex items-center gap-2 rounded-md border bg-white px-3 py-2 shadow-sm"
        :class="toast.type === 'error'
          ? 'border-red-200 text-red-600'
          : toast.type === 'success'
            ? 'border-green-200 text-green-600'
            : 'border-slate-200 text-slate-700'"
        role="status"
        aria-live="polite"
      >
        <span class="text-sm font-medium">{{ toast.msg }}</span>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
